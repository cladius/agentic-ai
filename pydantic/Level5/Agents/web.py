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

load_dotenv()

logfire_token = os.getenv('LOGFIRE_TOKEN')
if not logfire_token:
    print("Error: LOGFIRE_TOKEN not set. Please set it in your .env file.")
    logfire.error("LOGFIRE_TOKEN not set in web.py. Some features may not work.")
    logfire_token = "dummy_token_if_not_set"

logfire.configure(token=logfire_token)
logfire.info("Initializing web.py module for general web content operations")

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

CHROMA_DB_PATH = "./chroma_db"
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
embedding_function = embedding_functions.DefaultEmbeddingFunction()
web_content_general_collection = chroma_client.get_or_create_collection(name="web_content_general", embedding_function=embedding_function)

class WebUrlInput(BaseModel):
    """Pydantic model for web content extraction input."""
    web_url: str = Field(description="The full URL of the web page to extract content from.")
    output_file: Optional[str] = Field(None, description="Optional file path to save the extracted content locally.")

class WebQueryInput(BaseModel):
    """Pydantic model for querying web content."""
    web_url: str = Field(description="The web page URL to query.")
    question: str = Field(description="Question about the web page content.")

def check_web_content_in_db(url: str) -> Optional[dict]:
    """
    Checks ChromaDB for existing web content by URL.
    Returns content and metadata if found, else None.
    """
    try:
        results = web_content_general_collection.get(where={"url": url}, limit=1, include=['documents', 'metadatas'])
        if results['ids']:
            logfire.info(f"Found web content in ChromaDB for {url}")
            return {
                'id': results['ids'][0],
                'content': results['documents'][0],
                'metadata': results['metadatas'][0]
            }
        logfire.info(f"No web content found in ChromaDB for {url}")
        return None
    except Exception as e:
        logfire.error(f"ChromaDB query failed for {url}: {str(e)}")
        return None

def create_web_content_extractor_tool() -> Tool:
    """
    Creates a tool to extract textual content from web pages.
    Saves content to ChromaDB and optionally to a file.
    """
    async def extract_web_content(input_model: WebUrlInput) -> str:
        """
        Fetches and cleans textual content from a web page URL.
        Stores in ChromaDB, optionally saves to file, and returns content.
        """
        web_url = input_model.web_url
        output_file = input_model.output_file
        logfire.info(f"Web tool: Extracting content from web URL: {web_url}")

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
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            for script_or_style in soup(["script", "style", "nav", "footer", "header", "form"]):
                script_or_style.decompose()
            
            content_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'span', 'div']
            texts = [tag.get_text(separator=' ', strip=True) for tag in soup.find_all(content_tags) if tag.get_text(strip=True)]
            cleaned_text = ' '.join(filter(None, texts))
            
            cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
            
            if not cleaned_text:
                logfire.warning(f"Web tool: No robust textual content extracted from {web_url} using specific tags. Trying fallback.")
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

def create_web_query_tool() -> Tool:
    """
    Creates a tool to retrieve web content from ChromaDB for answering questions.
    Returns stored content or an error if not found.
    """
    async def query_web_content(input_model: WebQueryInput) -> str:
        """
        Retrieves web page content from ChromaDB by URL.
        Used by the agent to answer questions based on the content.
        """
        web_url = input_model.web_url
        question = input_model.question
        logfire.info(f"Web tool: Retrieving content for query on URL: {web_url}")

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
    Specialized agent for extracting and querying general web page content.
    Handles summarization and question answering using stored content.
    """
    def __init__(self, api_key: str):
        super().__init__(
            model='gemini-1.5-flash-latest',
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