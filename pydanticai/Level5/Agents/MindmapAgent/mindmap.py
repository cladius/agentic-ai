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
import graphviz
import pkg_resources
import uuid
import platform
import subprocess
import logfire
import chromadb
from chromadb.utils import embedding_functions

# Explicitly add Graphviz bin folder to PATH
GRAPHVIZ_BIN_PATH = r"C:\Program Files\Graphviz\bin"
os.environ["PATH"] += os.pathsep + GRAPHVIZ_BIN_PATH

# Load environment variables from .env file
load_dotenv()

# Initialize Logfire for logging
logfire_token = os.getenv('LOGFIRE_TOKEN')
if not logfire_token:
    print("Error: LOGFIRE_TOKEN not set. Please set it in your .env file.")
    exit(1)
logfire.configure(token=logfire_token)
logfire.info("Starting mindmap generation script")

# Fix for Windows event loop issue
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Initialize ChromaDB client for content storage
chroma_client = chromadb.PersistentClient(path="./chroma_db")
embedding_function = embedding_functions.DefaultEmbeddingFunction()
content_collection = chroma_client.get_or_create_collection(name="mindmap_content", embedding_function=embedding_function)
script_collection = chroma_client.get_or_create_collection(name="mindmap_scripts", embedding_function=embedding_function)
mindmap_collection = chroma_client.get_or_create_collection(name="mindmap_dots", embedding_function=embedding_function)

# 1. Define input models
class ContentInput(BaseModel):
    url: str = Field(description="The YouTube video or web page URL to extract content from.")
    output_file: str = Field(description="The file path to save the extracted content.")

class ScriptInput(BaseModel):
    input_file: str = Field(description="The file path containing the extracted content.")
    output_file: str = Field(description="The file path to save the generated script.")

class MindmapInput(BaseModel):
    script_file: str = Field(description="The file path containing the script to convert to a mindmap.")
    output_file: str = Field(description="The file path to save the generated mindmap image (PNG).")

# Helper function to extract YouTube video ID
def get_youtube_video_id(url: str) -> Optional[str]:
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

# Helper function to check Graphviz installation
def check_graphviz():
    try:
        result = subprocess.run(["dot", "-V"], capture_output=True, text=True, check=True)
        logfire.info(f"Graphviz installed: {result.stderr.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logfire.error(f"Graphviz check failed: {str(e)}")
        return False

# Helper function to check ChromaDB for existing content
def check_chroma_collection(collection, url: str, file_type: str) -> Optional[dict]:
    try:
        results = collection.get(where={"url": url})
        if results['ids']:
            logfire.info(f"Found {file_type} in ChromaDB for {url}")
            return {
                'id': results['ids'][0],
                'content': results['documents'][0],
                'metadata': results['metadatas'][0]
            }
        logfire.info(f"No {file_type} found in ChromaDB for {url}")
        return None
    except Exception as e:
        logfire.error(f"ChromaDB query failed for {url} ({file_type}): {str(e)}")
        return None

# 2. Content Extraction Tool
def create_content_extraction_tool() -> Tool:
    def extract_content(input_model: ContentInput) -> str:
        url = input_model.url
        output_file = input_model.output_file
        logfire.info(f"Extracting content from URL: {url}")

        # Check ChromaDB for existing content
        existing_content = check_chroma_collection(content_collection, url, "content")
        if existing_content:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(existing_content['content'])
            return f"Content retrieved from ChromaDB and saved to {output_file}"

        video_id = get_youtube_video_id(url)
        if video_id:
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US'])
                cleaned_transcript = ' '.join([entry['text'] for entry in transcript])
                cleaned_transcript = re.sub(r'\s+', ' ', cleaned_transcript).strip()
                if not cleaned_transcript:
                    logfire.error(f"Empty YouTube transcript for {url}")
                    return f"Error: Extracted YouTube transcript was empty for {url}."
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(cleaned_transcript)
                content_collection.add(
                    documents=[cleaned_transcript],
                    metadatas=[{'url': url, 'video_id': video_id}],
                    ids=[str(uuid.uuid4())]
                )
                logfire.info(f"Content saved to {output_file} and stored in ChromaDB")
                return f"Content extracted and saved to {output_file}"
            except NoTranscriptFound:
                logfire.error(f"No transcript found for video ID {video_id} ({url})")
                return f"Error: No transcript found for video ID {video_id} ({url})."
            except TranscriptsDisabled:
                logfire.error(f"Transcripts disabled for video ID {video_id} ({url})")
                return f"Error: Transcripts are disabled for video ID {video_id} ({url})."
            except VideoUnavailable:
                logfire.error(f"Video unavailable for video ID {video_id} ({url})")
                return f"Error: Video with ID {video_id} ({url}) is unavailable."
            except Exception as e:
                logfire.error(f"YouTube Transcript API error for {url}: {str(e)}")
                return f"YouTube Transcript API Error for {url}: {str(e)}."
        else:
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
                    metadatas=[{'url': url}],
                    ids=[str(uuid.uuid4())]
                )
                logfire.info(f"Content saved to {output_file} and stored in ChromaDB")
                return f"Content extracted and saved to {output_file}"
            except requests.exceptions.HTTPError as e:
                logfire.error(f"HTTP error for {url}: {e}")
                return f"Error: HTTP error for {url}: {e}"
            except requests.exceptions.RequestException as e:
                logfire.error(f"Failed to fetch {url}: {e}")
                return f"Error: Failed to fetch {url}: {e}"
            except Exception as e:
                logfire.error(f"Unexpected error for {url}: {e}")
                return f"Error: Unexpected error for {url}: {e}"

    return Tool[ContentInput](
        name="extract_content",
        description="Extracts content from a YouTube video (transcript) or web page (text), saves it to a file, and stores it in ChromaDB.",
        function=extract_content
    )

# 3. Script Generation Tool
def create_script_generation_tool() -> Tool:
    def generate_script(input_model: ScriptInput) -> str:
        input_file = input_model.input_file
        output_file = input_model.output_file
        url = None
        logfire.info(f"Generating script from: {input_file}")

        # Extract URL from input file name or content
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            if not content:
                logfire.error(f"Input file {input_file} is empty")
                return f"Error: Input file {input_file} is empty."
            # Attempt to extract URL from metadata or file context
            existing_script = check_chroma_collection(script_collection, input_file, "script")
            if existing_script:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(existing_script['content'])
                return existing_script['content']
        except FileNotFoundError:
            logfire.error(f"Input file {input_file} not found")
            return f"Error: Input file {input_file} not found."
        except Exception as e:
            logfire.error(f"Failed to read {input_file}: {str(e)}")
            return f"Error: Failed to read {input_file}: {str(e)}."

        return content  # Return content for summarization by the agent

    return Tool[ScriptInput](
        name="generate_script",
        description="Reads content from a file, generates a summary, saves it to a file, and stores it in ChromaDB.",
        function=generate_script
    )

# 4. Mindmap Generation Tool
def create_mindmap_generation_tool() -> Tool:
    def generate_mindmap(input_model: MindmapInput) -> str:
        script_file = input_model.script_file
        output_file = input_model.output_file
        logfire.info(f"Generating mindmap from: {script_file}")

        # Check ChromaDB for existing DOT content
        existing_mindmap = check_chroma_collection(mindmap_collection, script_file, "mindmap")
        if existing_mindmap:
            dot_content = existing_mindmap['content']
            try:
                graph = graphviz.Source(dot_content, format='png')
                graph.render(filename=output_file.replace('.png', ''), cleanup=True)
                logfire.info(f"Mindmap image rendered from ChromaDB content to {output_file}")
                return dot_content
            except Exception as e:
                logfire.error(f"Failed to render mindmap from ChromaDB content: {str(e)}")
                return f"Error: Failed to render mindmap from ChromaDB content: {str(e)}"

        try:
            with open(script_file, 'r', encoding='utf-8') as f:
                script_text = f.read()
            if not script_text:
                logfire.error(f"Script file {script_file} is empty")
                return f"Error: Script file {script_file} is empty."
            return script_text  # Return script content for the agent to process
        except FileNotFoundError:
            logfire.error(f"Script file {script_file} not found")
            return f"Error: Script file {script_file} not found."
        except Exception as e:
            logfire.error(f"Failed to read {script_file}: {str(e)}")
            return f"Error: Failed to read {script_file}: {str(e)}"

    return Tool[MindmapInput](
        name="generate_mindmap",
        description="Reads the script from a file, generates a Graphviz DOT string, and stores it in ChromaDB.",
        function=generate_mindmap
    )

# Main execution block
async def main():
    parser = argparse.ArgumentParser(description="Generate a mindmap image from a YouTube video or web URL.")
    parser.add_argument("url", type=str, help="The YouTube video or web page URL to process.")
    args = parser.parse_args()

    # Validate Graphviz
    if not check_graphviz():
        logfire.error(f"Graphviz 'dot' command not found at {GRAPHVIZ_BIN_PATH}")
        print(f"Error: Graphviz 'dot' command not found. Ensure {GRAPHVIZ_BIN_PATH} is correct and contains dot.exe.")
        return

    # Retrieve API key
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        logfire.error("GEMINI_API_KEY not set")
        print("Error: GEMINI_API_KEY not set. Please set it in your .env file.")
        return

    # Check library versions
    try:
        pydantic_ai_version = pkg_resources.get_distribution("pydantic-ai").version
        graphviz_version = pkg_resources.get_distribution("graphviz").version
        logfire.info(f"pydantic-ai version: {pydantic_ai_version}")
        logfire.info(f"graphviz version: {graphviz_version}")
    except pkg_resources.DistributionNotFound as e:
        logfire.error(f"Missing library: {str(e)}")
        print(f"Error: Missing library: {str(e)}. Install with `pip install pydantic-ai graphviz`.")
        return

    # Generate unique file names
    unique_id = str(uuid.uuid4())
    content_file = f"content_{unique_id}.txt"
    script_file = f"script_{unique_id}.txt"
    mindmap_file = f"mindmap_{unique_id}.png"
    dot_file = f"mindmap_{unique_id}.dot"

    try:
        # Content Extraction Agent
        content_tool = create_content_extraction_tool()
        content_agent = Agent(
            model="google-gla:gemini-2.0-flash",
            api_key=gemini_api_key,
            tools=[content_tool],
            system_prompt="Extract content from the provided URL and save it to the specified file using the extract_content tool."
        )
        logfire.info(f"Attempting to extract content from: {args.url}")
        print(f"Attempting to extract content from: {args.url}")
        content_response = await content_agent.run(
            f"Extract content from this URL and save it to {content_file}: {args.url}"
        )
        content_output = content_response.output if hasattr(content_response, 'output') else str(content_response)
        logfire.info(f"Content extraction result: {content_output}")
        print(f"DEBUG: Content extraction result: {content_output}")
        if "Error" in content_output:
            print(f"Content extraction failed: {content_output}")
            return

        # Script Generation Agent
        script_tool = create_script_generation_tool()
        script_agent = Agent(
            model="google-gla:gemini-2.0-flash",
            api_key=gemini_api_key,
            tools=[script_tool],
            system_prompt=(
                "Read the content from the input file using the generate_script tool. "
                "Generate a concise 150-200 word summary, focusing on main topics and key takeaways. "
                "Return the summary as a string and save it to the output file."
            )
        )
        logfire.info(f"Attempting to generate script from: {content_file}")
        print(f"Attempting to generate script from: {content_file}")
        script_response = await script_agent.run(
            f"Generate a script from {content_file} and save it to {script_file}"
        )
        script_output = script_response.output if hasattr(script_response, 'output') else str(script_response)
        logfire.info(f"Script generation result: {script_output[:100]}...")
        print(f"DEBUG: Script generation result: {script_output}")
        if "Error" in script_output:
            print(f"Script generation failed: {script_output}")
            return
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(script_output)
        script_collection.add(
            documents=[script_output],
            metadatas=[{'url': args.url, 'input_file': content_file}],
            ids=[str(uuid.uuid4())]
        )
        logfire.info(f"Script saved to {script_file} and stored in ChromaDB")
        print(f"DEBUG: Script saved to {script_file}")

        # Mindmap Generation Agent
        mindmap_tool = create_mindmap_generation_tool()
        mindmap_agent = Agent(
            model="google-gla:gemini-2.0-flash",
            api_key=gemini_api_key,
            tools=[mindmap_tool],
            system_prompt=(
                "Use the generate_mindmap tool to read the content from the script file. "
                "Analyze the content to identify the main topic, subtopics, and key details. "
                "Generate a Graphviz DOT language string representing a hierarchical mindmap structure. "
                "The DOT content must: "
                "- Start with 'digraph G { rankdir=LR; node [shape=box, style=filled, fillcolor=lightblue];'. "
                "- Include a main node for the central topic. "
                "- Include subnodes for major subtopics connected to the main node. "
                "- Include additional nodes for key details connected to their respective subtopics. "
                "- Use proper Graphviz syntax (e.g., 'node1 -> node2;'). "
                "- Ensure node labels are concise and relevant to the script content. "
                "Return only the DOT string, without any additional text or explanations."
            )
        )
        logfire.info(f"Attempting to generate mindmap structure from: {script_file}")
        print(f"Attempting to generate mindmap structure from: {script_file}")
        mindmap_response = await mindmap_agent.run(
            f"Use the generate_mindmap tool to read the script from {script_file} and generate a Graphviz DOT string for a mindmap."
        )
        dot_content = mindmap_response.output if hasattr(mindmap_response, 'output') else str(mindmap_response)
        logfire.info(f"Generated DOT content (first 200 chars): {dot_content[:200]}...")
        print(f"DEBUG: Generated DOT content (first 200 chars): {dot_content[:200]}...")

        # Validate and render the mindmap
        try:
            if not dot_content.startswith('digraph G'):
                logfire.error(f"Invalid DOT content generated: {dot_content[:200]}...")
                print(f"Error: Invalid DOT content generated: {dot_content[:200]}...")
                return
            with open(dot_file, 'w', encoding='utf-8') as f:
                f.write(dot_content)
            mindmap_collection.add(
                documents=[dot_content],
                metadatas=[{'url': args.url, 'script_file': script_file, 'output_file': mindmap_file}],
                ids=[str(uuid.uuid4())]
            )
            logfire.info(f"DOT content saved to {dot_file} and stored in ChromaDB")
            print(f"DEBUG: DOT file saved to {dot_file}")

            # Render mindmap using graphviz
            graph = graphviz.Source(dot_content, format='png')
            graph.render(filename=mindmap_file.replace('.png', ''), cleanup=True)
            logfire.info(f"Mindmap image saved to {mindmap_file}")
            print(f"DEBUG: Mindmap image saved to {mindmap_file}")
            print(f"\n--- Mindmap Generation Result ---")
            print(f"Mindmap image generated successfully and saved to {mindmap_file}")
        except Exception as e:
            logfire.error(f"Failed to render mindmap image: {str(e)}")
            print(f"Error: Failed to render mindmap image: {str(e)}. Check Graphviz installation and DOT content.")
            print(f"DEBUG: Problematic DOT content: {dot_content[:500]}...")
            return

    except Exception as e:
        logfire.error(f"Unexpected error: {str(e)}")
        print(f"\nAn unexpected error occurred: {e}")
        print("Please ensure:")
        print("1. All libraries are installed: `pip install pydantic-ai==0.2.17 requests beautifulsoup4 python-dotenv graphviz youtube-transcript-api logfire chromadb`")
        print(f"2. Graphviz is installed and {GRAPHVIZ_BIN_PATH} contains dot.exe.")
        print("3. GEMINI_API_KEY and LOGFIRE_TOKEN are set in your .env file.")
        print("4. The YouTube video has public captions enabled, or the web page has extractable text.")
        print(f"5. pydantic-ai version is compatible (current: {pydantic_ai_version if 'pydantic_ai_version' in locals() else 'unknown'}).")
        print(f"6. graphviz version is installed (current: {graphviz_version if 'graphviz_version' in locals() else 'unknown'}).")

if __name__ == "__main__":
    asyncio.run(main())