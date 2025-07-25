import os
import asyncio
from typing import Optional
import logfire
from pydantic import BaseModel, Field
from pydantic_ai import Agent, Tool
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
import chromadb
from chromadb.utils import embedding_functions
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import platform
import google.generativeai as genai
import re

load_dotenv()

logfire_token = os.getenv('LOGFIRE_TOKEN')
if not logfire_token:
    print("Error: LOGFIRE_TOKEN not set in .env file.")
    logfire.error("LOGFIRE_TOKEN not set in youtube.py")
    logfire_token = "dummy_token_if_not_set"
logfire.configure(token=logfire_token)
logfire.info("Starting youtube.py module for YouTube transcript processing")

CHROMA_DB_PATH = "./chroma_db"
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
youtube_transcript_collection = chroma_client.get_or_create_collection(
    name="youtube_transcripts", embedding_function=embedding_functions.DefaultEmbeddingFunction()
)

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

def get_youtube_video_id(url: str) -> Optional[str]:
    """
    Extracts the YouTube video ID from a URL.
    Returns the ID if valid (11 characters, alphanumeric or specific symbols), else None.
    """
    try:
        parsed_url = urlparse(url)
        if parsed_url.hostname in ('youtu.be', 'www.youtube.com', 'youtube.com'):
            if parsed_url.hostname == 'youtu.be':
                video_id = parsed_url.path[1:]
            else:
                query = parse_qs(parsed_url.query)
                video_id = query.get('v', [None])[0]
            if video_id and re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
                return video_id
        logfire.error(f"Invalid YouTube URL: {url}")
        return None
    except Exception as e:
        logfire.error(f"Error parsing YouTube URL {url}: {str(e)}")
        return None

def check_youtube_transcript_in_db(url: str) -> Optional[dict]:
    """
    Checks ChromaDB for an existing YouTube transcript by URL.
    Returns transcript and metadata if found, else None.
    """
    try:
        results = youtube_transcript_collection.get(where={"url": url}, limit=1, include=['documents', 'metadatas'])
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

async def try_with_retry(operation, max_attempts=5, base_delay=3):
    """
    Retries an async operation with exponential backoff.
    Handles API errors like 429/503 with retries.
    """
    for attempt in range(max_attempts):
        try:
            return await operation()
        except Exception as e:
            if any(code in str(e) for code in ["429", "503"]) and attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                logfire.warn(f"API error on attempt {attempt + 1}, retrying after {delay}s", error=str(e))
                await asyncio.sleep(delay)
            else:
                logfire.error(f"Operation failed after {attempt + 1} attempts", error=str(e))
                raise Exception(f"Error: API unavailable (429/503) or other error. Please check your Gemini API quota at https://console.cloud.google.com/apis/api/aiplatform.googleapis.com/quotas or try again later: {str(e)}")
    raise Exception(f"Error: API unavailable (429/503) after {max_attempts} attempts.")

class YouTubeTranscriptInput(BaseModel):
    """Pydantic model for YouTube transcript extraction input."""
    youtube_url: str = Field(description="The YouTube video URL to extract the transcript from.")

class YouTubeQueryInput(BaseModel):
    """Pydantic model for querying YouTube transcript content."""
    youtube_url: str = Field(description="The YouTube video URL to query.")
    question: str = Field(description="Question about the YouTube video content.")

def create_youtube_transcript_tool() -> Tool:
    """Creates a tool to extract transcripts from YouTube videos."""
    async def get_youtube_transcript(input_model: YouTubeTranscriptInput) -> str:
        """
        Extracts the transcript from a YouTube video URL.
        Stores the transcript in ChromaDB and returns it.
        """
        youtube_url = input_model.youtube_url
        logfire.info(f"Extracting transcript for YouTube URL: {youtube_url}")

        video_id = get_youtube_video_id(youtube_url)
        if not video_id:
            return f"Error: Invalid YouTube URL: {youtube_url}. Ensure it has a valid 11-character video ID."

        existing_transcript = check_youtube_transcript_in_db(youtube_url)
        if existing_transcript:
            logfire.info(f"Returning cached transcript for {youtube_url}")
            return existing_transcript['content']

        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US', 'en-GB'])
            transcript_text = " ".join(item['text'] for item in transcript_list).strip()
            transcript_text = re.sub(r'\s+', ' ', transcript_text)

            if not transcript_text:
                logfire.warning(f"No transcript content extracted for {youtube_url}")
                return f"Error: No transcript content extracted for {youtube_url}"

            youtube_transcript_collection.add(
                documents=[transcript_text],
                metadatas=[{'url': youtube_url, 'source': 'youtube_transcript'}],
                ids=[video_id]
            )
            logfire.info(f"Transcript stored in ChromaDB for {youtube_url}")
            return transcript_text
        except NoTranscriptFound:
            logfire.error(f"No transcript available for {youtube_url}")
            return f"Error: No transcript available for {youtube_url}. The video may not have captions."
        except TranscriptsDisabled:
            logfire.error(f"Transcripts disabled for {youtube_url}")
            return f"Error: Transcripts are disabled for {youtube_url}"
        except Exception as e:
            logfire.error(f"Failed to extract transcript for {youtube_url}: {str(e)}")
            return f"Error: Failed to extract transcript for {youtube_url}: {str(e)}"

    return Tool[YouTubeTranscriptInput](
        name="get_youtube_transcript",
        description="Extracts the transcript from a YouTube video URL and stores it in ChromaDB.",
        function=get_youtube_transcript
    )

def create_youtube_query_tool() -> Tool:
    """Creates a tool to answer questions about YouTube video transcripts."""
    async def query_youtube_transcript(input_model: YouTubeQueryInput) -> str:
        """
        Answers a question about a YouTube video using its stored transcript.
        Uses Gemini model to generate a concise answer.
        """
        youtube_url = input_model.youtube_url
        question = input_model.question
        logfire.info(f"Answering question for YouTube URL: {youtube_url}, Question: {question}")

        existing_transcript = check_youtube_transcript_in_db(youtube_url)
        if not existing_transcript:
            logfire.warning(f"No transcript found for {youtube_url}. Run 'get_youtube_transcript' first.")
            return f"Error: No transcript found for {youtube_url}. Please extract the transcript first using 'get_youtube_transcript'."

        try:
            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
            model = genai.GenerativeModel('gemini-1.5-flash')

            async def query():
                """
                Generates an answer to a question using a YouTube transcript.
                Ensures the answer is concise and based solely on the transcript.
                """
                prompt = (
                    f"Based on the following YouTube transcript, answer the question: {question}\n\n"
                    f"Transcript:\n{existing_transcript['content']}\n\n"
                    "Provide a concise and accurate answer (50-100 words) based only on the transcript. "
                    "If the transcript lacks details to answer the question, state that clearly."
                )
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: model.generate_content([prompt])
                )
                answer = response.text
                word_count = len(answer.split())
                if word_count > 100:
                    raise ValueError(f"Answer length {word_count} words exceeds 100-word limit.")
                return answer

            answer = await try_with_retry(query)
            logfire.info(f"Answered question for {youtube_url}: {answer[:50]}...")
            return answer
        except Exception as e:
            logfire.error(f"YouTube query failed for {youtube_url}: {str(e)}")
            return f"Error: Failed to answer question for {youtube_url}: {str(e)}"

    return Tool[YouTubeQueryInput](
        name="query_youtube_transcript",
        description="Answers a question about a YouTube video using its stored transcript from ChromaDB.",
        function=query_youtube_transcript
    )

class YouTubeAgent(Agent):
    """
    Specialized agent for extracting YouTube transcripts and answering questions.
    Uses youtube_transcript_api and Gemini model for processing.
    """
    def __init__(self, api_key: str):
        super().__init__(
            model=GeminiModel('gemini-1.5-flash-latest', provider=GoogleGLAProvider(api_key=api_key)),
            api_key=api_key,
            tools=[
                create_youtube_transcript_tool(),
                create_youtube_query_tool()
            ],
            system_prompt=(
                'You are an expert YouTube content assistant capable of extracting transcripts and answering questions. '
                '1. **Transcript Extraction**: Use the `get_youtube_transcript` tool to fetch and store transcripts from YouTube URLs. '
                '2. **Question Answering**: Use the `query_youtube_transcript` tool to answer questions based on stored transcripts. '
                '3. **Summarization**: Summarize transcripts (150-250 words) when requested, focusing on main points. '
                '4. **Error Handling**: Provide clear error messages for invalid URLs, missing transcripts, or API issues. '
                'Store transcripts in ChromaDB with URL metadata and use only verified data.'
            )
        )
        self.youtube_transcript_collection = youtube_transcript_collection