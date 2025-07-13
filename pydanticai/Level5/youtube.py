import os
from typing import Optional
import re
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
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
    logfire.error("LOGFIRE_TOKEN not set in youtube.py. Some features may not work.")
    logfire_token = "dummy_token_if_not_set"

logfire.configure(token=logfire_token)
logfire.info("Initializing youtube.py module for transcript operations")

# Fix Windows event loop issue
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Initialize ChromaDB client for content storage
CHROMA_DB_PATH = "./chroma_db"
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
embedding_function = embedding_functions.DefaultEmbeddingFunction()
# Dedicated collection for YouTube transcripts
youtube_transcript_collection = chroma_client.get_or_create_collection(name="youtube_transcripts", embedding_function=embedding_function)

# Input models for Pydantic validation
class YouTubeUrlInput(BaseModel):
    """
    Pydantic model for YouTube transcript extraction tool input.
    """
    youtube_url: str = Field(description="The full URL of the YouTube video to summarize.")
    output_file: Optional[str] = Field(None, description="Optional file path to save the extracted transcript locally.")

class YouTubeQueryInput(BaseModel):
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
        # Handle various YouTube domains and path formats
        if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
            if parsed_url.path == '/watch':
                return parse_qs(parsed_url.query).get('v', [None])[0]
            elif parsed_url.path.startswith('/embed/'):
                return parsed_url.path.split('/embed/')[1].split('?')[0]
            elif parsed_url.path.startswith('/v/'):
                return parsed_url.path.split('/v/')[1].split('?')[0]
        elif parsed_url.hostname == 'youtu.be':
            return parsed_url.path[1:].split('?')[0]
        return None
    except Exception as e:
        logfire.error(f"Failed to parse YouTube video ID from {url}: {str(e)}")
        return None

# Helper function to check if captions are available using YouTube's oEmbed endpoint
def check_video_availability_via_oembed(video_id: str) -> bool:
    """
    Checks video availability and basic info using YouTube's oEmbed endpoint.
    A successful response often indicates the video exists and is public.
    """
    try:
        oembed_url = f"https://www.youtube.com/oembed?url=http://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.get(oembed_url, timeout=5)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        logfire.info(f"oEmbed check for video ID {video_id}: available")
        return True
    except requests.RequestException as e:
        logfire.error(f"oEmbed check failed for video ID {video_id}: {str(e)}")
        return False

# Helper function to check ChromaDB for existing YouTube transcript
def check_youtube_transcript_in_db(url: str) -> Optional[dict]:
    """
    Queries ChromaDB for YouTube transcript using URL as the identifier.
    Returns a dictionary with 'content' and 'metadata' if found, None otherwise.
    """
    try:
        results = youtube_transcript_collection.get(where={"url": url}, limit=1, include=['documents', 'metadatas'])
        if results['ids']:
            logfire.info(f"Found YouTube transcript in ChromaDB for {url}")
            return {
                'id': results['ids'][0],
                'content': results['documents'][0], # Correctly access the document content
                'metadata': results['metadatas'][0]
            }
        logfire.info(f"No YouTube transcript found in ChromaDB for {url}")
        return None
    except Exception as e:
        logfire.error(f"ChromaDB query failed for {url}: {str(e)}")
        return None

# YouTube Transcript Extraction Tool
def create_youtube_transcript_tool() -> Tool:
    """
    Creates a pydantic-ai Tool for fetching YouTube video transcripts.
    """
    async def get_youtube_transcript(input_model: YouTubeUrlInput) -> str:
        """
        Fetches the transcript from a YouTube video URL and saves it to a file and ChromaDB.
        Returns the raw transcript content.
        """
        youtube_url = input_model.youtube_url
        output_file = input_model.output_file
        logfire.info(f"YouTube tool: Extracting transcript from YouTube URL: {youtube_url}")

        # Check ChromaDB for existing transcript
        existing_content = check_youtube_transcript_in_db(youtube_url)
        if existing_content:
            transcript_content = existing_content['content']
            if output_file:
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(transcript_content)
                    logfire.info(f"YouTube tool: Transcript retrieved from ChromaDB and saved to {output_file}")
                except IOError as io_e:
                    logfire.error(f"YouTube tool: Could not save transcript to {output_file}: {io_e}")
            return transcript_content

        video_id = get_youtube_video_id(youtube_url)
        if not video_id:
            logfire.error(f"YouTube tool: Invalid YouTube video URL: {youtube_url}")
            return f"Error: Invalid YouTube video URL: {youtube_url}. Please provide a valid URL."

        if not check_video_availability_via_oembed(video_id):
            return f"Error: YouTube video {youtube_url} appears to be unavailable or private."

        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US'])
            cleaned_transcript = ' '.join([entry['text'] for entry in transcript])
            cleaned_transcript = re.sub(r'\s+', ' ', cleaned_transcript).strip()
            if not cleaned_transcript:
                logfire.error(f"YouTube tool: Empty transcript for video ID {video_id}")
                return f"Error: Extracted transcript was empty for {youtube_url}. This might mean no spoken content or very short video."

            # Save transcript to file if output_file is specified
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(cleaned_transcript)
                logfire.info(f"YouTube tool: Transcript saved to {output_file}")

            # Store in ChromaDB
            youtube_transcript_collection.add(
                documents=[cleaned_transcript],
                metadatas=[{'url': youtube_url, 'video_id': video_id, 'source': 'youtube_transcript'}],
                ids=[str(uuid.uuid4())]
            )
            logfire.info(f"YouTube tool: Transcript stored in ChromaDB for {youtube_url}")
            return cleaned_transcript
        except TranscriptsDisabled:
            logfire.error(f"YouTube tool: Transcripts disabled for {youtube_url}")
            return f"Error: Transcripts are disabled by the video creator for {youtube_url}. Captions are not enabled."
        except NoTranscriptFound:
            logfire.error(f"YouTube tool: No English transcript found for {youtube_url}")
            return f"Error: No English transcript found for {youtube_url}. Try another video or a different language."
        except VideoUnavailable:
            logfire.error(f"YouTube tool: Video unavailable for {youtube_url}")
            return f"Error: Video with ID {video_id} ({youtube_url}) is unavailable. It might be deleted or private."
        except Exception as e:
            logfire.error(f"YouTube tool: Failed to fetch transcript for {youtube_url}: {str(e)}")
            return f"Error: Failed to fetch transcript for {youtube_url}. Details: {str(e)}."

    return Tool[YouTubeUrlInput](
        name="get_youtube_transcript",
        description="Extracts the English transcript from a YouTube video URL, saves it to a file (optional), and stores it in ChromaDB. Returns the raw transcript text.",
        function=get_youtube_transcript
    )

# YouTube Content Query Tool
def create_youtube_query_tool() -> Tool:
    """
    Creates a pydantic-ai Tool for querying stored YouTube transcripts.
    """
    async def query_youtube_content(input_model: YouTubeQueryInput) -> str:
        """
        Retrieves transcript from ChromaDB and returns it for answering questions.
        The actual Q&A logic will be handled by the Agent's LLM, not this tool.
        This tool's role is just to provide the relevant transcript.
        """
        youtube_url = input_model.youtube_url
        question = input_model.question
        logfire.info(f"YouTube tool: Retrieving content for query on URL: {youtube_url}")

        # Check ChromaDB for transcript
        content_data = check_youtube_transcript_in_db(youtube_url)
        if content_data:
            return content_data['content']
        
        logfire.warning(f"YouTube tool: No transcript found in ChromaDB for {youtube_url} when querying.")
        return f"Error: No transcript found for {youtube_url}. Please extract the transcript first using 'get_youtube_transcript'."

    return Tool[YouTubeQueryInput](
        name="query_youtube_content",
        description="Retrieves the full YouTube video transcript from ChromaDB given a URL. The agent then uses this transcript to answer questions about the video.",
        function=query_youtube_content
    )

class YouTubeAgent(Agent):
    """
    A specialized agent for interacting with YouTube video transcripts.
    Can extract transcripts and answer questions based on them.
    """
    def __init__(self, api_key: str):
        super().__init__(
            model='google-gla:gemini-1.5-flash', # Using flash for cost-effectiveness, pro if higher quality needed
            api_key=api_key,
            tools=[
                create_youtube_transcript_tool(),
                create_youtube_query_tool()
            ],
            system_prompt=(
                'You are a helpful YouTube assistant capable of extracting video transcripts and answering questions about them.'
                '1. **Transcript Extraction:** Use the `get_youtube_transcript` tool to fetch the raw text of a YouTube video transcript.'
                '2. **Summarization:** If asked to summarize, provide a concise (150-250 words) summary of the extracted transcript, highlighting main points and key takeaways.'
                '3. **Question Answering:** If asked a question about a video, use the `query_youtube_content` tool to retrieve the relevant transcript and then answer the question directly and accurately based *only* on the content of the transcript.'
                '4. **Error Handling:** Always report clearly if a transcript cannot be found, is disabled, or if the video is unavailable.'
            )
        )
        self.youtube_transcript_collection = youtube_transcript_collection