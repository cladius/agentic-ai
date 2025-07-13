import os
import argparse
import requests
from pydantic import BaseModel, Field
from pydantic_ai import Agent, Tool
from dotenv import load_dotenv
import logfire
import chromadb
from chromadb.utils import embedding_functions
import uuid
import asyncio
import platform
from typing import Optional  # Added import for Optional

# Load environment variables from .env file
load_dotenv()

# Initialize Logfire for logging
logfire_token = os.getenv('LOGFIRE_TOKEN')
if not logfire_token:
    print("Error: LOGFIRE_TOKEN not set. Please set it in your .env file.")
    exit(1)
logfire.configure(token=logfire_token)
logfire.info("Starting web content summarization script")

# Fix Windows event loop issue
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Initialize ChromaDB client for content storage
chroma_client = chromadb.PersistentClient(path="./chroma_db")
embedding_function = embedding_functions.DefaultEmbeddingFunction()
content_collection = chroma_client.get_or_create_collection(name="web_content", embedding_function=embedding_function)

# Input models for Pydantic validation
class UrlExtractionInput(BaseModel):
    """
    Pydantic model for URL content extraction tool input.
    """
    url: str = Field(description="The URL from which to extract content.")
    output_file: str = Field(description="File path to save the extracted content.")

class QueryInput(BaseModel):
    """
    Pydantic model for content query tool input.
    """
    url: str = Field(description="The URL to query.")
    question: str = Field(description="Question about the web content.")

# Helper function to check ChromaDB for existing content
def check_content_in_db(url: str) -> Optional[dict]:
    """
    Queries ChromaDB for content using URL as the identifier.
    Returns None if no content is found, or a dict with id, content, and metadata.
    """
    try:
        results = content_collection.get(where={"url": url})
        if results['ids']:
            logfire.info(f"Found content in ChromaDB for {url}")
            return {
                'id': results['ids'][0],
                'content': results['documents'][0],
                'metadata': results['metadatas'][0]
            }
        logfire.info(f"No content found in ChromaDB for {url}")
        return None
    except Exception as e:
        logfire.error(f"ChromaDB query failed for {url}: {str(e)}")
        return None

# Tavily Extract API Tool
def create_tavily_extractor_tool(api_key: str) -> Tool:
    """
    Creates a pydantic-ai Tool for extracting content from URLs using Tavily Extract API.
    """
    if not api_key:
        logfire.error("TAVILY_API_KEY is required")
        raise ValueError("TAVILY_API_KEY is required for the Tavily Extractor tool.")

    def tavily_extract_content(input_model: UrlExtractionInput) -> str:
        """
        Extracts content from a URL using Tavily Extract API, saves it to a file, and stores it in ChromaDB.
        """
        url = input_model.url
        output_file = input_model.output_file
        logfire.info(f"Extracting content from URL: {url}")

        # Check ChromaDB for existing content
        existing_content = check_content_in_db(url)
        if existing_content:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(existing_content['content'])
            return existing_content['content']

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        payload = {
            "urls": [url],
            "include_images": False,
            "extract_depth": "basic"
        }

        try:
            response = requests.post("https://api.tavily.com/extract", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if data and data.get("results") and data["results"][0].get("raw_content"):
                content = data["results"][0]["raw_content"]
                
                # Save content to file
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Store in ChromaDB
                content_collection.add(
                    documents=[content],
                    metadatas=[{'url': url}],
                    ids=[str(uuid.uuid4())]
                )
                logfire.info(f"Content saved to {output_file} and stored in ChromaDB")
                return content
            else:
                logfire.error(f"No content extracted from {url}")
                return f"Error: No content extracted or unexpected response structure from Tavily for URL: {url}"
        except requests.exceptions.RequestException as e:
            logfire.error(f"Tavily API error for {url}: {str(e)}")
            return f"Error communicating with Tavily Extract API for {url}: {e}"
        except Exception as e:
            logfire.error(f"Unexpected error during content extraction for {url}: {str(e)}")
            return f"Error: An unexpected error occurred during content extraction for {url}: {e}"

    return Tool[UrlExtractionInput](
        name="extract_url_content",
        description="Extracts the main textual content from a URL using Tavily Extract API, saves it to a file, and stores it in ChromaDB.",
        function=tavily_extract_content
    )

# Content Query Tool
def create_content_query_tool() -> Tool:
    """
    Creates a pydantic-ai Tool for answering questions based on stored web content.
    """
    def query_content(input_model: QueryInput) -> str:
        """
        Retrieves content from ChromaDB and returns it for answering questions.
        """
        url = input_model.url
        question = input_model.question
        logfire.info(f"Answering question '{question}' for URL: {url}")

        # Check ChromaDB for content
        content_data = check_content_in_db(url)
        if content_data:
            return content_data['content']
        
        logfire.error(f"No content found in ChromaDB for {url}")
        return f"Error: No content found for {url}. Please process the URL first."

    return Tool[QueryInput](
        name="query_web_content",
        description="Retrieves web content from ChromaDB to answer questions.",
        function=query_content
    )

# Main execution block
async def main():
    """
    Main function to summarize web content and provide an interactive CLI for content queries.
    """
    parser = argparse.ArgumentParser(
        description="Extract, summarize, and query content from a URL using a Pydantic-AI agent."
    )
    parser.add_argument(
        "url",
        type=str,
        help="The URL from which to extract content and summarize."
    )
    args = parser.parse_args()

    # Retrieve API keys
    tavily_api_key = os.getenv('TAVILY_API_KEY')
    gemini_api_key = os.getenv('GEMINI_API_KEY')

    if not tavily_api_key:
        logfire.error("TAVILY_API_KEY not set")
        print("Error: TAVILY_API_KEY not set. Please set it in your .env file.")
        exit(1)
    if not gemini_api_key:
        logfire.error("GEMINI_API_KEY not set")
        print("Error: GEMINI_API_KEY not set. Please set it in your .env file.")
        exit(1)

    # Generate unique file name for content
    unique_id = str(uuid.uuid4())
    content_file = f"content_{unique_id}.txt"

    try:
        # Create tools
        tavily_extractor_tool = create_tavily_extractor_tool(tavily_api_key)
        query_tool = create_content_query_tool()

        # Initialize the Summarization Agent
        summary_agent = Agent(
            model='google-gla:gemini-1.5-flash',
            api_key=gemini_api_key,
            tools=[tavily_extractor_tool],
            system_prompt=(
                'You are an expert content extractor and summarizer. '
                'Use the `extract_url_content` tool to extract the content from the provided URL. '
                'Then, provide a concise, high-quality summary of the extracted text (150-200 words). '
                'Focus on main topics, key takeaways, and important details. '
                'If the content extraction fails or no relevant content is found, report the issue clearly.'
            )
        )

        # Extract and summarize content
        logfire.info(f"Attempting to extract and summarize content from: {args.url}")
        print(f"\nAttempting to extract and summarize content from: {args.url}\n")
        summary_response = await summary_agent.run(
            f"Extract the content from this URL and save it to {content_file}, then provide a comprehensive summary (150-200 words): {args.url}"
        )
        summary_output = summary_response.output if hasattr(summary_response, 'output') else str(summary_response)
        logfire.info(f"Summary generation result: {summary_output[:100]}...")
        print("\n--- Web Content Summary ---")
        print(summary_output)

        if "Error" in summary_output:
            return

        # Initialize the Query Agent for interactive Q&A
        query_agent = Agent(
            model='google-gla:gemini-1.5-flash',
            api_key=gemini_api_key,
            tools=[query_tool],
            system_prompt=(
                'You are an expert in answering questions about web content. '
                'Use the `query_web_content` tool to retrieve the content for the given URL. '
                'Answer the user\'s question based on the retrieved content. '
                'Provide a concise, accurate, and relevant response. '
                'If the content is unavailable, report the issue clearly.'
            )
        )

        # Interactive Q&A session
        print("\n--- Interactive Q&A ---")
        print(f"Content extracted from {args.url}. Ask questions about the content or type 'exit' to quit.")
        while True:
            question = input("Question: ").strip()
            if question.lower() == 'exit':
                logfire.info("Exiting Q&A session")
                print("Exiting Q&A session.")
                break
            logfire.info(f"User asked: {question}")
            query_response = await query_agent.run(
                f"Using the content from {args.url}, answer this question: {question}"
            )
            query_output = query_response.output if hasattr(query_response, 'output') else str(query_response)
            logfire.info(f"Query response: {query_output}")
            print(f"Answer: {query_output}\n")

    except Exception as e:
        logfire.error(f"Unexpected error: {str(e)}")
        print(f"\nError: {e}")
        print("Please ensure:")
        print("1. Libraries are installed: `pip install requests pydantic-ai python-dotenv logfire chromadb`")
        print("2. TAVILY_API_KEY, GEMINI_API_KEY, and LOGFIRE_TOKEN are set in your .env file.")
        print("3. The URL is valid and accessible.")
        print(f"4. Content may be saved to {content_file} if extraction was successful.")

if __name__ == "__main__":
    asyncio.run(main())