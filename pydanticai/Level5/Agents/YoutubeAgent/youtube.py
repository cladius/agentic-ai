import argparse
import os
from typing import Optional
import re
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from pydantic import BaseModel, Field
from pydantic_ai import Agent, Tool
from dotenv import load_dotenv
import requests
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
    exit(1)
logfire.configure(token=logfire_token)
logfire.info("Starting YouTube transcript summarization script")

# Fix Windows event loop issue
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Initialize ChromaDB client for content storage
chroma_client = chromadb.PersistentClient(path="./chroma_db")
embedding_function = embedding_functions.DefaultEmbeddingFunction()
content_collection = chroma_client.get_or_create_collection(name="youtube_transcripts", embedding_function=embedding_function)

# Input models for Pydantic validation
class YouTubeUrlInput(BaseModel):
    """
    Pydantic model for YouTube transcript extraction tool input.
    """
    youtube_url: str = Field(description="The full URL of the YouTube video to summarize.")
    output_file: str = Field(description="File path to save the extracted transcript.")

class QueryInput(BaseModel):
    """
    Pydantic model for content query tool input.
    """
    youtube_url: str = Field(description="The YouTube video URL to query.")
    question: str = Field(description="Question about the video content.")

# Helper function to extract video ID from YouTube URL
def get_youtube_video_id(url: str) -> Optional[str]:
    """
    Extracts the YouTube video ID from a given URL.
    Supports standard, shortened, and embed URLs.
    """
    try:
        parsed_url = urlparse(url)
        if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
            if parsed_url.path == '/watch':
                return parse_qs(parsed_url.query).get('v', [None])[0]
            elif parsed_url.path.startswith('/embed/'):
                return parsed_url.path.split('/embed/')[1].split('?')[0]
        elif parsed_url.hostname == 'youtu.be':
            return parsed_url.path[1:].split('?')[0]
        return None
    except Exception as e:
        logfire.error(f"Failed to parse YouTube video ID from {url}: {str(e)}")
        return None

# Helper function to check if captions are available
def check_captions_available(video_id: str) -> bool:
    """
    Checks if captions are available using YouTube's oEmbed endpoint.
    """
    try:
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}"
        response = requests.get(oembed_url, timeout=5)
        logfire.info(f"Captions check for video ID {video_id}: {'available' if response.status_code == 200 else 'unavailable'}")
        return response.status_code == 200
    except requests.RequestException as e:
        logfire.error(f"Captions check failed for video ID {video_id}: {str(e)}")
        return False

# Helper function to check ChromaDB for existing content
def check_content_in_db(url: str) -> Optional[dict]:
    """
    Queries ChromaDB for transcript using URL as the identifier.
    """
    try:
        results = content_collection.get(where={"url": url})
        if results['ids']:
            logfire.info(f"Found transcript in ChromaDB for {url}")
            return {
                'id': results['ids'][0],
                'content': results['documents'][0],
                'metadata': results['metadatas'][0]
            }
        logfire.info(f"No transcript found in ChromaDB for {url}")
        return None
    except Exception as e:
        logfire.error(f"ChromaDB query failed for {url}: {str(e)}")
        return None

# YouTube Transcript Extraction Tool
def create_youtube_transcript_tool() -> Tool:
    """
    Creates a pydantic-ai Tool for fetching YouTube video transcripts.
    """
    def youtube_transcript_extractor(input_model: YouTubeUrlInput) -> str:
        """
        Fetches the transcript from a YouTube video URL and saves it to a file and ChromaDB.
        """
        youtube_url = input_model.youtube_url
        output_file = input_model.output_file
        logfire.info(f"Extracting transcript from YouTube URL: {youtube_url}")

        # Check ChromaDB for existing transcript
        existing_content = check_content_in_db(youtube_url)
        if existing_content:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(existing_content['content'])
            return existing_content['content']

        video_id = get_youtube_video_id(youtube_url)
        if not video_id:
            logfire.error(f"Invalid YouTube video URL: {youtube_url}")
            return f"Error: Invalid YouTube video URL: {youtube_url}. Please provide a valid URL."

        if not check_captions_available(video_id):
            logfire.error(f"Captions may not be available for {youtube_url}")
            return f"Error: Captions may not be available for {youtube_url}. Check if 'CC' is enabled on YouTube."

        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US'])
            cleaned_transcript = ' '.join([entry['text'] for entry in transcript])
            cleaned_transcript = re.sub(r'\s+', ' ', cleaned_transcript).strip()
            if not cleaned_transcript:
                logfire.error(f"Empty transcript for video ID {video_id}")
                return f"Error: Extracted transcript was empty for {youtube_url}."

            # Save transcript to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_transcript)

            # Store in ChromaDB
            content_collection.add(
                documents=[cleaned_transcript],
                metadatas=[{'url': youtube_url, 'video_id': video_id}],
                ids=[str(uuid.uuid4())]
            )
            logfire.info(f"Transcript saved to {output_file} and stored in ChromaDB")
            return cleaned_transcript
        except TranscriptsDisabled:
            logfire.error(f"Transcripts disabled for {youtube_url}")
            return f"Error: Transcripts are disabled for {youtube_url}. Captions are not enabled."
        except NoTranscriptFound:
            logfire.error(f"No English transcript found for {youtube_url}")
            return f"Error: No English transcript found for {youtube_url}. Try another video."
        except Exception as e:
            logfire.error(f"Failed to fetch transcript for {youtube_url}: {str(e)}")
            return f"Error: Failed to fetch transcript for {youtube_url}. Details: {str(e)}."

    return Tool[YouTubeUrlInput](
        name="get_youtube_transcript",
        description="Extracts the transcript from a YouTube video URL, saves it to a file, and stores it in ChromaDB.",
        function=youtube_transcript_extractor
    )

# Content Query Tool
def create_content_query_tool() -> Tool:
    """
    Creates a pydantic-ai Tool for answering questions based on stored YouTube transcripts.
    """
    def query_content(input_model: QueryInput) -> str:
        """
        Retrieves transcript from ChromaDB and returns it for answering questions.
        """
        youtube_url = input_model.youtube_url
        question = input_model.question
        logfire.info(f"Answering question '{question}' for URL: {youtube_url}")

        # Check ChromaDB for transcript
        content_data = check_content_in_db(youtube_url)
        if content_data:
            return content_data['content']
        
        logfire.error(f"No transcript found in ChromaDB for {youtube_url}")
        return f"Error: No transcript found for {youtube_url}. Please process the URL first."

    return Tool[QueryInput](
        name="query_youtube_content",
        description="Retrieves YouTube video transcript from ChromaDB to answer questions.",
        function=query_content
    )

# Main execution block
async def main():
    """
    Main function to summarize a YouTube video and provide an interactive CLI for content queries.
    """
    parser = argparse.ArgumentParser(
        description="Extract, summarize, and query a YouTube video transcript using a Pydantic-AI agent with Gemini."
    )
    parser.add_argument(
        "youtube_url",
        type=str,
        help="The YouTube video URL to summarize."
    )
    args = parser.parse_args()

    # Retrieve the Gemini API key
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        logfire.error("GEMINI_API_KEY not set")
        print("Error: GEMINI_API_KEY not set. Please set it in your .env file.")
        print("Get an API key from Google Cloud Console and enable the Generative Language API.")
        exit(1)

    # Generate unique file name for transcript
    unique_id = str(uuid.uuid4())
    transcript_file = f"transcript_{unique_id}.txt"

    try:
        # Create tools
        transcript_tool = create_youtube_transcript_tool()
        query_tool = create_content_query_tool()

        # Initialize the Summarization Agent
        summary_agent = Agent(
            model='google-gla:gemini-2.0-flash',
            api_key=gemini_api_key,
            tools=[transcript_tool],
            system_prompt=(
                'You are an expert YouTube video summarizer. '
                'Use the `get_youtube_transcript` tool to extract the transcript from the provided YouTube video URL. '
                'Then, provide a concise, high-quality summary of the video content (150-200 words). '
                'Focus on main topics, key takeaways, and important details. '
                'If the transcript is unavailable or an error occurs, report the issue clearly without attempting to summarize.'
            )
        )

        # Extract and summarize transcript
        logfire.info(f"Attempting to summarize YouTube video: {args.youtube_url}")
        print(f"\nAttempting to summarize YouTube video: {args.youtube_url}\n")
        summary_response = await summary_agent.run(
            f"Extract the transcript from this YouTube video URL and save it to {transcript_file}, then provide a summary (150-200 words): {args.youtube_url}"
        )
        summary_output = summary_response.output if hasattr(summary_response, 'output') else str(summary_response)
        logfire.info(f"Summary generation result: {summary_output[:100]}...")
        print("\n--- YouTube Video Summary ---")
        print(summary_output)

        if "Error" in summary_output:
            return

        # Initialize the Query Agent for interactive Q&A
        query_agent = Agent(
            model='google-gla:gemini-2.0-flash',
            api_key=gemini_api_key,
            tools=[query_tool],
            system_prompt=(
                'You are an expert in answering questions about YouTube video content. '
                'Use the `query_youtube_content` tool to retrieve the transcript for the given YouTube URL. '
                'Answer the user\'s question based on the retrieved transcript. '
                'Provide a concise, accurate, and relevant response. '
                'If the transcript is unavailable, report the issue clearly.'
            )
        )

        # Interactive Q&A session
        print("\n--- Interactive Q&A ---")
        print(f"Content extracted from {args.youtube_url}. Ask questions about the video content or type 'exit' to quit.")
        while True:
            question = input("Question: ").strip()
            if question.lower() == 'exit':
                logfire.info("Exiting Q&A session")
                print("Exiting Q&A session.")
                break
            logfire.info(f"User asked: {question}")
            query_response = await query_agent.run(
                f"Using the transcript from {args.youtube_url}, answer this question: {question}"
            )
            query_output = query_response.output if hasattr(query_response, 'output') else str(query_response)
            logfire.info(f"Query response: {query_output}")
            print(f"Answer: {query_output}\n")

    except Exception as e:
        logfire.error(f"Unexpected error: {str(e)}")
        print(f"\nError: {e}")
        print("Please ensure:")
        print("1. Libraries are installed: `pip install youtube_transcript_api pydantic-ai python-dotenv requests logfire chromadb`")
        print("2. GEMINI_API_KEY and LOGFIRE_TOKEN are set in your .env file.")
        print("3. The YouTube video has English captions enabled (check for 'CC' button).")
        print(f"4. Transcript may be saved to {transcript_file} if extraction was successful.")

if __name__ == "__main__":
    asyncio.run(main())