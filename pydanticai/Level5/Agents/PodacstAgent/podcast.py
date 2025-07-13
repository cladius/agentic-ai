import os
import argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from typing import Optional
import re
import asyncio
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, Tool
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment
import io
import subprocess
import importlib.metadata
import uuid
import platform
import logfire
import chromadb
from chromadb.utils import embedding_functions

# Load environment variables from .env file
load_dotenv()

# Initialize Logfire for logging
logfire.configure(token=os.getenv('LOGFIRE_TOKEN'))
logfire.info("Starting podcast generation script")

# Fix Windows event loop issue
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Initialize ChromaDB client for content storage
chroma_client = chromadb.PersistentClient(path="./chroma_db")
embedding_function = embedding_functions.DefaultEmbeddingFunction()
content_collection = chroma_client.get_or_create_collection(name="content", embedding_function=embedding_function)
script_collection = chroma_client.get_or_create_collection(name="scripts", embedding_function=embedding_function)
audio_collection = chroma_client.get_or_create_collection(name="audio_metadata", embedding_function=embedding_function)

# Input models for Pydantic validation
class ContentInput(BaseModel):
    url: str = Field(description="YouTube video or web page URL to extract content from")
    output_file: str = Field(description="File path to save the extracted content")

class ScriptInput(BaseModel):
    input_file: str = Field(description="File path of the extracted content")
    output_file: str = Field(description="File path to save the generated script")

class AudioInput(BaseModel):
    script_file: str = Field(description="File path of the script to convert to audio")
    output_file: str = Field(description="File path to save the generated audio podcast")

class QueryInput(BaseModel):
    url: str = Field(description="URL of the content to query")
    question: str = Field(description="Question about the content")

# Helper function to extract YouTube video ID from URL
def get_youtube_video_id(url: str) -> Optional[str]:
    """Extracts YouTube video ID from a given URL."""
    try:
        parsed_url = urlparse(url)
        if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
            if parsed_url.path == '/watch':
                return parse_qs(parsed_url.query).get('v', [None])[0]
            elif parsed_url.path.startswith('/embed'):
                return parsed_url.path.split('/embed/')[1].split('?')[0]
        elif parsed_url.hostname == 'youtu.be':
            return parsed_url.path[1:].split('?')[0]
        return None
    except Exception as e:
        logfire.error(f"Failed to parse YouTube video ID from {url}: {str(e)}")
        return None

# Helper function to verify FFmpeg installation
def check_ffmpeg() -> bool:
    """Checks if FFmpeg is installed and accessible in the system PATH or FFMPEG_PATH."""
    ffmpeg_path = os.getenv('FFMPEG_PATH', 'ffmpeg')
    try:
        subprocess.run([ffmpeg_path, "-version"], capture_output=True, check=True)
        logfire.info("FFmpeg is installed and accessible")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logfire.error(f"FFmpeg check failed: {str(e)}")
        return False

# Helper function to check ChromaDB for existing content
def check_content_in_db(identifier: str, collection, metadata_key: str) -> Optional[dict]:
    """Queries ChromaDB for content using metadata filtering."""
    try:
        results = collection.get(where={metadata_key: identifier})
        if results['ids']:
            return {
                'id': results['ids'][0],
                'content': results['documents'][0],
                'metadata': results['metadatas'][0]
            }
        return None
    except Exception as e:
        logfire.error(f"ChromaDB query failed for {identifier}: {str(e)}")
        return None

# Content Extraction Tool
def create_content_extraction_tool() -> Tool:
    """Creates a tool to extract content from YouTube videos or web pages."""
    def extract_content(input_model: ContentInput) -> str:
        url = input_model.url
        output_file = input_model.output_file
        logfire.info(f"Extracting content from URL: {url}")

        # Check ChromaDB for existing content
        existing_content = check_content_in_db(url, content_collection, 'url')
        if existing_content:
            logfire.info(f"Content found in ChromaDB for {url}")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(existing_content['content'])
            return f"Content retrieved from database and saved to {output_file}"

        # Handle YouTube URLs
        video_id = get_youtube_video_id(url)
        if video_id:
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US'])
                cleaned_transcript = ' '.join([entry['text'] for entry in transcript])
                cleaned_transcript = re.sub(r'\s+', ' ', cleaned_transcript).strip()
                if not cleaned_transcript:
                    logfire.error(f"Empty transcript for video ID {video_id}")
                    return f"Error: Extracted YouTube transcript was empty for {url}."
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(cleaned_transcript)
                content_collection.add(
                    documents=[cleaned_transcript],
                    metadatas=[{'url': url, 'source': 'youtube'}],
                    ids=[str(uuid.uuid4())]
                )
                logfire.info(f"Content saved to {output_file} and stored in ChromaDB")
                return f"Content extracted and saved to {output_file}"
            except NoTranscriptFound:
                logfire.error(f"No transcript found for video ID {video_id}")
                return f"Error: No transcript found for video ID {video_id} ({url})."
            except TranscriptsDisabled:
                logfire.error(f"Transcripts disabled for video ID {video_id}")
                return f"Error: Transcripts are disabled for video ID {video_id} ({url})."
            except VideoUnavailable:
                logfire.error(f"Video unavailable for video ID {video_id}")
                return f"Error: Video with ID {video_id} ({url}) is unavailable."
            except Exception as e:
                logfire.error(f"YouTube Transcript API error: {str(e)}")
                return f"YouTube Transcript API Error for {url}: {str(e)}."
        
        # Handle web page URLs
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            for script in soup(["script", "style"]):
                script.decompose()
            text = soup.get_text(separator=' ', strip=True)
            cleaned_text = ' '.join(text.split())
            if not cleaned_text:
                logfire.error(f"No textual content extracted from {url}")
                return f"Error: No textual content extracted from {url}."
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
            content_collection.add(
                documents=[cleaned_text],
                metadatas=[{'url': url, 'source': 'web'}],
                ids=[str(uuid.uuid4())]
            )
            logfire.info(f"Content saved to {output_file} and stored in ChromaDB")
            return f"Content extracted and saved to {output_file}"
        except requests.exceptions.HTTPError as e:
            logfire.error(f"HTTP error for {url}: {str(e)}")
            return f"Error: HTTP error for {url}: {e}"
        except requests.exceptions.RequestException as e:
            logfire.error(f"Request error for {url}: {str(e)}")
            return f"Error: Failed to fetch {url}: {e}"
        except Exception as e:
            logfire.error(f"Unexpected error for {url}: {str(e)}")
            return f"Error: Unexpected error for {url}: {e}"

    return Tool[ContentInput](
        name="extract_content",
        description="Extracts content from a YouTube video (transcript) or web page (text) and saves it to a file.",
        function=extract_content
    )

# Script Generation Tool
def create_script_generation_tool() -> Tool:
    """Creates a tool to generate a summary script from extracted content."""
    def generate_script(input_model: ScriptInput) -> str:
        input_file = input_model.input_file
        output_file = input_model.output_file
        logfire.info(f"Generating script from {input_file}")

        # Check ChromaDB for existing script
        existing_script = check_content_in_db(input_file, script_collection, 'input_file')
        if existing_script:
            logfire.info(f"Script found in ChromaDB for {input_file}")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(existing_script['content'])
            return existing_script['content']

        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            if not content:
                logfire.error(f"Input file {input_file} is empty")
                return f"Error: Input file {input_file} is empty."
            logfire.info(f"Content length: {len(content)}")
            script_collection.add(
                documents=[content],
                metadatas=[{'input_file': input_file}],
                ids=[str(uuid.uuid4())]
            )
            return content
        except FileNotFoundError:
            logfire.error(f"Input file {input_file} not found")
            return f"Error: Input file {input_file} not found."
        except Exception as e:
            logfire.error(f"Failed to read {input_file}: {str(e)}")
            return f"Error: Failed to read {input_file}: {str(e)}"

    return Tool[ScriptInput](
        name="generate_script",
        description="Reads content from a file and returns it for summarization.",
        function=generate_script
    )

# Audio Generation Tool
def create_audio_generation_tool(elevenlabs_api_key: str) -> Tool:
    """Creates a tool to convert a script into a two-person audio podcast with distinct female and male voices."""
    if not elevenlabs_api_key:
        logfire.error("ELEVENLABS_API_KEY not set")
        raise ValueError("ELEVENLABS_API_KEY not set.")
    elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)

    def generate_audio(input_model: AudioInput) -> str:
        script_file = input_model.script_file
        output_file = input_model.output_file
        logfire.info(f"Generating audio from {script_file}")

        # Check ChromaDB for existing audio
        existing_audio = check_content_in_db(script_file, audio_collection, 'script_file')
        if existing_audio and os.path.exists(existing_audio['metadata']['output_file']):
            logfire.info(f"Audio already exists for {script_file} at {existing_audio['metadata']['output_file']}")
            return f"Audio podcast already exists at {existing_audio['metadata']['output_file']}"

        try:
            with open(script_file, 'r', encoding='utf-8') as f:
                summary_text = f.read()
            if not summary_text:
                logfire.error(f"Script file {script_file} is empty")
                return f"Error: Script file {script_file} is empty."
            logfire.info(f"Script text length: {len(summary_text)}")

            # Split script into sentences for alternating voices
            sentences = re.split(r'(?<=[.!?])\s+', summary_text.strip())
            sentences = [s.strip() for s in sentences if s.strip()]
            logfire.info(f"Split into {len(sentences)} sentences")

            # Use distinct female and male voices
            voice_ids = ["EXAVITQu4vr4xnSDxMaL", "ErXwobaYiN019PkySvjV"]  # Sarah (female), Adam (male)

            combined_audio = AudioSegment.silent(duration=0)
            for i, sentence in enumerate(sentences):
                voice_id = voice_ids[i % 2]  # Alternate between female and male voices
                logfire.info(f"Generating audio for sentence {i+1} with voice {voice_id}")
                audio_stream = elevenlabs_client.text_to_speech.convert(
                    text=sentence,
                    voice_id=voice_id
                )
                buffer = io.BytesIO()
                for chunk in audio_stream:
                    buffer.write(chunk)
                buffer.seek(0)
                sentence_audio = AudioSegment.from_file(buffer, format="mp3")
                combined_audio += sentence_audio
                if i < len(sentences) - 1:
                    combined_audio += AudioSegment.silent(duration=500)  # Add 500ms pause between sentences
                logfire.info(f"Audio for sentence {i+1} generated")

            if not combined_audio:
                logfire.error("No audio generated")
                return "Error: No audio generated."
            logfire.info(f"Exporting combined audio to {output_file}")
            combined_audio.export(output_file, format="mp3")
            audio_collection.add(
                documents=[script_file],
                metadatas=[{'script_file': script_file, 'output_file': output_file}],
                ids=[str(uuid.uuid4())]
            )
            logfire.info("Audio export complete and metadata stored in ChromaDB")
            return f"Audio podcast generated successfully and saved to {output_file}"
        except FileNotFoundError:
            logfire.error(f"Script file {script_file} not found")
            return f"Error: Script file {script_file} not found."
        except AttributeError as e:
            logfire.error(f"ElevenLabs API method error: {str(e)}")
            return f"Error: ElevenLabs API method error: {str(e)}. Ensure elevenlabs==2.3.0."
        except Exception as e:
            if "quota_exceeded" in str(e).lower():
                logfire.error(f"ElevenLabs quota exceeded: {str(e)}")
                return (
                    f"Error: ElevenLabs quota exceeded. You have insufficient credits for this request. "
                    f"Please upgrade your plan, purchase additional credits, or wait for your quota to reset. "
                    f"Check your account at https://elevenlabs.io/. Details: {str(e)}"
                )
            logfire.error(f"Audio generation error: {str(e)}")
            return f"Error: Failed to generate audio podcast: {str(e)}. Check ElevenLabs API key and FFmpeg."

    return Tool[AudioInput](
        name="generate_audio",
        description="Converts a script into a two-person audio podcast using ElevenLabs with alternating female and male voices.",
        function=generate_audio
    )

# Content Query Tool
def create_content_query_tool() -> Tool:
    """Creates a tool to answer questions based on extracted content."""
    def query_content(input_model: QueryInput) -> str:
        url = input_model.url
        question = input_model.question
        logfire.info(f"Answering question '{question}' for URL: {url}")

        # Check ChromaDB for content
        content_data = check_content_in_db(url, content_collection, 'url')
        if content_data:
            return content_data['content']
        
        logfire.error(f"No content found in ChromaDB for {url}")
        return f"Error: No content found for {url}. Please process the URL first."

    return Tool[QueryInput](
        name="query_content",
        description="Retrieves content for a given URL to answer questions.",
        function=query_content
    )

# Main execution with interactive CLI
async def main():
    """Main function to process a URL and provide an interactive CLI for content queries."""
    parser = argparse.ArgumentParser(description="Generate an audio podcast from a YouTube video or web URL and answer content-related questions.")
    parser.add_argument("url", type=str, help="The YouTube video or web page URL to process.")
    args = parser.parse_args()

    # Validate dependencies and API keys
    if not check_ffmpeg():
        logfire.error("FFmpeg is not installed or not in PATH")
        print("Error: FFmpeg is not installed or not in PATH. Set FFMPEG_PATH in .env or ensure it's in system PATH.")
        return

    gemini_api_key = os.getenv('GEMINI_API_KEY')
    elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
    logfire_api_key = os.getenv('LOGFIRE_TOKEN')

    if not gemini_api_key:
        logfire.error("GEMINI_API_KEY not set")
        print("Error: GEMINI_API_KEY not set. Please set it in your .env file.")
        return
    if not elevenlabs_api_key:
        logfire.error("ELEVENLABS_API_KEY not set")
        print("Error: ELEVENLABS_API_KEY not set. Please set it in your .env file.")
        return
    if not logfire_api_key:
        logfire.error("LOGFIRE_TOKEN not set")
        print("Error: LOGFIRE_TOKEN not set. Please set it in your .env file.")
        return

    # Check library versions
    try:
        pydantic_ai_version = importlib.metadata.version("pydantic-ai")
        elevenlabs_version = importlib.metadata.version("elevenlabs")
        logfire.info(f"pydantic-ai version: {pydantic_ai_version}")
        logfire.info(f"elevenlabs version: {elevenlabs_version}")
    except importlib.metadata.PackageNotFoundError as e:
        logfire.error(f"Missing library: {str(e)}")
        print(f"Error: Missing library: {str(e)}. Install with `pip install pydantic-ai elevenlabs logfire chromadb`.")
        return

    # Generate unique file names
    unique_id = str(uuid.uuid4())
    content_file = f"content_{unique_id}.txt"
    script_file = f"script_{unique_id}.txt"
    audio_file = f"podcast_{unique_id}.mp3"

    try:
        # Extract content
        content_tool = create_content_extraction_tool()
        content_agent = Agent(
            model="google-gla:gemini-2.0-flash",
            api_key=gemini_api_key,
            tools=[content_tool],
            system_prompt="Extract content from the provided URL and save it to the specified file using the extract_content tool."
        )
        logfire.info(f"Attempting to extract content from: {args.url}")
        content_response = await content_agent.run(
            f"Extract content from this URL and save it to {content_file}: {args.url}"
        )
        content_output = content_response.output if hasattr(content_response, 'output') else str(content_response)
        logfire.info(f"Content extraction result: {content_output}")
        if "Error" in content_output:
            print(f"Content extraction failed: {content_output}")
            return

        # Generate script
        script_tool = create_script_generation_tool()
        script_agent = Agent(
            model="google-gla:gemini-2.0-flash",
            api_key=gemini_api_key,
            tools=[script_tool],
            system_prompt=(
                "Read the content from the input file using the generate_script tool. "
                "Generate a concise 100-150 word summary, focusing on main topics and key takeaways. "
                "Ensure the summary is relevant to the content. Return the summary as a string."
            )
        )
        logfire.info(f"Attempting to generate script from: {content_file}")
        script_response = await script_agent.run(
            f"Generate a script from {content_file} and save it to {script_file}"
        )
        script_output = script_response.output if hasattr(script_response, 'output') else str(script_response)
        logfire.info(f"Script generation result: {script_output}")
        if "Error" in script_output:
            print(f"Script generation failed: {script_output}")
            return
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(script_output)
        script_collection.add(
            documents=[script_output],
            metadatas=[{'input_file': content_file}],
            ids=[str(uuid.uuid4())]
        )
        logfire.info(f"Script saved to {script_file} and stored in ChromaDB")

        # Generate audio
        audio_tool = create_audio_generation_tool(elevenlabs_api_key)
        audio_agent = Agent(
            model="google-gla:gemini-2.0-flash",
            api_key=gemini_api_key,
            tools=[audio_tool],
            system_prompt="Convert the script from the input file into a two-person audio podcast using the generate_audio tool and save it to the specified file."
        )
        logfire.info(f"Attempting to generate audio from: {script_file}")
        audio_response = await audio_agent.run(
            f"Generate an audio podcast from {script_file} and save it to {audio_file}"
        )
        audio_output = audio_response.output if hasattr(audio_response, 'output') else str(audio_response)
        logfire.info(f"Podcast generation result: {audio_output}")
        print(f"\n--- Podcast Generation Result ---")
        print(audio_output)

        # Interactive CLI for content queries
        query_tool = create_content_query_tool()
        query_agent = Agent(
            model="google-gla:gemini-2.0-flash",
            api_key=gemini_api_key,
            tools=[query_tool],
            system_prompt=(
                "Use the query_content tool to retrieve content for the given URL. "
                "Answer the user's question based on the retrieved content. "
                "Provide a concise and accurate response."
            )
        )
        print("\n--- Interactive Q&A ---")
        print(f"Content extracted from {args.url}. Ask questions about the content or type 'exit' to quit.")
        while True:
            question = input("Question: ").strip()
            if question.lower() == 'exit':
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
        print(f"\nAn unexpected error occurred: {e}")
        print("Please ensure:")
        print("1. All libraries are installed: `pip install pydantic-ai==0.2.17 requests beautifulsoup4 python-dotenv elevenlabs==2.3.0 pydub youtube-transcript-api logfire chromadb`")
        print("2. FFmpeg is installed and accessible via PATH or FFMPEG_PATH in .env.")
        print("3. GEMINI_API_KEY, ELEVENLABS_API_KEY, and LOGFIRE_TOKEN are set in your .env file.")
        print("4. The YouTube video has public captions enabled, or the web page has extractable text.")
        print(f"5. pydantic-ai version is compatible (current: {pydantic_ai_version if 'pydantic_ai_version' in locals() else 'unknown'}).")
        print(f"6. elevenlabs version is ==2.3.0 (current: {elevenlabs_version if 'elevenlabs_version' in locals() else 'unknown'}).")

if __name__ == "__main__":
    asyncio.run(main())