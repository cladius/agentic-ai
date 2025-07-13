import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import Optional
import re
from pydantic import BaseModel, Field
from pydantic_ai import Agent, Tool
from dotenv import load_dotenv
import logfire
import chromadb
from chromadb.utils import embedding_functions
import uuid
import asyncio
import platform

# Load environment variables from .env file
load_dotenv()

# Initialize Logfire for logging
logfire_token = os.getenv('LOGFIRE_TOKEN')
if not logfire_token:
    print("Error: LOGFIRE_TOKEN not set. Please set it in your .env file.")
    logfire.error("LOGFIRE_TOKEN not set in web.py. Some features may not work.")
    logfire_token = "dummy_token_if_not_set"

logfire.configure(token=logfire_token)
logfire.info("Initializing web.py module for general web content operations")

# Fix Windows event loop issue if any async operations are used (e.g., for future enhancements)
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Initialize ChromaDB client for content storage
CHROMA_DB_PATH = "./chroma_db"
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
embedding_function = embedding_functions.DefaultEmbeddingFunction()
# Dedicated collection for general web content
web_content_general_collection = chroma_client.get_or_create_collection(name="web_content_general", embedding_function=embedding_function)

# Input models for Pydantic validation
class WebUrlInput(BaseModel):
    """
    Pydantic model for general web page content extraction tool input.
    """
    web_url: str = Field(description="The full URL of the web page to extract content from.")
    output_file: Optional[str] = Field(None, description="Optional file path to save the extracted content locally.")

class WebQueryInput(BaseModel):
    """
    Pydantic model for general web content query tool input.
    """
    web_url: str = Field(description="The web page URL to query.")
    question: str = Field(description="Question about the web page content.")

# Helper function to check ChromaDB for existing web content
def check_web_content_in_db(url: str) -> Optional[dict]:
    """
    Queries ChromaDB for general web content using URL as the identifier.
    Returns a dictionary with 'content' and 'metadata' if found, None otherwise.
    """
    try:
        results = web_content_general_collection.get(where={"url": url}, limit=1, include=['documents', 'metadatas'])
        if results['ids']:
            logfire.info(f"Found web content in ChromaDB for {url}")
            return {
                'id': results['ids'][0],
                'content': results['documents'][0], # Correctly access the document content
                'metadata': results['metadatas'][0]
            }
        logfire.info(f"No web content found in ChromaDB for {url}")
        return None
    except Exception as e:
        logfire.error(f"ChromaDB query failed for {url}: {str(e)}")
        return None

# General Web Content Extraction Tool
def create_web_content_extractor_tool() -> Tool:
    """
    Creates a pydantic-ai Tool for extracting general textual content from web pages.
    """
    async def extract_web_content(input_model: WebUrlInput) -> str:
        """
        Fetches the content from a general web page URL and saves it to a file and ChromaDB.
        Returns the raw textual content.
        """
        web_url = input_model.web_url
        output_file = input_model.output_file
        logfire.info(f"Web tool: Extracting content from web URL: {web_url}")

        # Check ChromaDB for existing content
        existing_content = check_web_content_in_db(web_url)
        if existing_content:
            content_text = existing_content['content']
            if output_file:
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(content_text)
                    logfire.info(f"Web tool: Content retrieved from ChromaDB and saved to {output_file}")
                except IOError as io_e:
                    logfire.error(f"Web tool: Could not save content to {output_file}: {io_e}")
            return content_text

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(web_url, headers=headers, timeout=15)
            response.raise_for_status() # Raise an exception for HTTP errors

            soup = BeautifulSoup(response.text, 'html.parser')
            # Remove script, style, navigation, footer, header, form elements
            for script_or_style in soup(["script", "style", "nav", "footer", "header", "form"]):
                script_or_style.decompose()
            
            # Get text from common content containers, prefer specific tags
            content_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'span', 'div']
            texts = [tag.get_text(separator=' ', strip=True) for tag in soup.find_all(content_tags) if tag.get_text(strip=True)]
            cleaned_text = ' '.join(filter(None, texts)) # Remove empty strings and join
            
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
            
            if not cleaned_text:
                logfire.warning(f"Web tool: No robust textual content extracted from {web_url} using specific tags. Trying fallback.")
                # Fallback to general text if specific tags fail or are empty
                cleaned_text = soup.get_text(separator=' ', strip=True)
                cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
                if not cleaned_text:
                    logfire.error(f"Web tool: Still no textual content extracted from {web_url}")
                    return f"Error: No textual content extracted from {web_url}. The page might be empty, heavily JavaScript-driven, or difficult to parse."

            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(cleaned_text)
                logfire.info(f"Web tool: Content saved to {output_file}")
            
            web_content_general_collection.add(
                documents=[cleaned_text],
                metadatas=[{'url': web_url, 'source': 'web_scrape'}],
                ids=[str(uuid.uuid4())]
            )
            logfire.info(f"Web tool: Web content stored in ChromaDB for {web_url}")
            return cleaned_text
        except requests.exceptions.HTTPError as e:
            logfire.error(f"Web tool: HTTP error for {web_url}: {e}")
            return f"Error: HTTP error for {web_url}: {e}"
        except requests.exceptions.RequestException as e:
            logfire.error(f"Web tool: Failed to fetch {web_url}: {e}")
            return f"Error: Failed to fetch {web_url}: {e}"
        except Exception as e:
            logfire.error(f"Web tool: Unexpected error for {web_url}: {e}")
            return f"Error: Unexpected error for {web_url}: {e}"

    return Tool[WebUrlInput](
        name="extract_web_content",
        description="Extracts raw textual content from a general web page URL, saves it to a file (optional), and stores it in ChromaDB. Returns the raw content text.",
        function=extract_web_content
    )

# General Web Content Query Tool
def create_web_query_tool() -> Tool:
    """
    Creates a pydantic-ai Tool for querying stored general web content.
    """
    async def query_web_content(input_model: WebQueryInput) -> str:
        """
        Retrieves general web page content from ChromaDB and returns it for answering questions.
        The actual Q&A logic will be handled by the Agent's LLM, not this tool.
        This tool's role is just to provide the relevant content.
        """
        web_url = input_model.web_url
        question = input_model.question # The question is used by the agent, not the tool directly
        logfire.info(f"Web tool: Retrieving content for query on URL: {web_url}")

        # Check ChromaDB for content
        content_data = check_web_content_in_db(web_url)
        if content_data:
            return content_data['content']
        
        logfire.warning(f"Web tool: No web content found in ChromaDB for {web_url} when querying.")
        return f"Error: No content found for {web_url}. Please extract the content first using 'extract_web_content'."

    return Tool[WebQueryInput](
        name="query_web_content",
        description="Retrieves the full textual content of a general web page from ChromaDB given a URL. The agent then uses this content to answer questions about the page.",
        function=query_web_content
    )

class WebAgent(Agent):
    """
    A specialized agent for interacting with general web page content.
    Can extract content and answer questions based on it.
    """
    def __init__(self, api_key: str):
        super().__init__(
            model='google-gla:gemini-1.5-flash', # Using flash for cost-effectiveness, pro if higher quality needed
            api_key=api_key,
            tools=[
                create_web_content_extractor_tool(),
                create_web_query_tool()
            ],
            system_prompt=(
                'You are a helpful web content assistant capable of extracting text from web pages and answering questions about them.'
                '1. **Content Extraction:** Use the `extract_web_content` tool to fetch the raw text of a web page.'
                '2. **Summarization:** If asked to summarize, provide a concise (150-250 words) summary of the extracted text, highlighting main points and key takeaways.'
                '3. **Question Answering:** If asked a question about a web page, use the `query_web_content` tool to retrieve the relevant text and then answer the question directly and accurately based *only* on the content of the page.'
                '4. **Error Handling:** Always report clearly if content cannot be extracted or if the URL is invalid.'
            )
        )
        self.web_content_general_collection = web_content_general_collection