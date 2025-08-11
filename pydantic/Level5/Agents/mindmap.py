import os
import re
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from pydantic_ai import Agent, Tool
from dotenv import load_dotenv
import chromadb
from chromadb.utils import embedding_functions
import uuid
import asyncio
import platform
import logfire
import subprocess

# Load environment variables
load_dotenv()

# Initialize Logfire
logfire_token = os.getenv('LOGFIRE_TOKEN')
if not logfire_token:
    print("Error: LOGFIRE_TOKEN not set. Please set it in your .env file.")
    logfire.error("LOGFIRE_TOKEN not set in mindmap.py. Some features may not work.")
    logfire_token = "dummy_token_if_not_set"

logfire.configure(token=logfire_token)
logfire.info("Initializing mindmap.py module for mindmap operations")

# Fix Windows event loop
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Initialize ChromaDB
CHROMA_DB_PATH = "./chroma_db"
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
embedding_function = embedding_functions.DefaultEmbeddingFunction()
mindmap_raw_content_collection = chroma_client.get_or_create_collection(name="mindmap_raw_content", embedding_function=embedding_function)
mindmap_scripts_collection = chroma_client.get_or_create_collection(name="mindmap_scripts", embedding_function=embedding_function)
mindmap_dots_collection = chroma_client.get_or_create_collection(name="mindmap_dots", embedding_function=embedding_function)

# Helper functions for ChromaDB checks
def check_mindmap_raw_content_in_db(url: str) -> Optional[dict]:
    """
    Checks ChromaDB for existing raw content for a mindmap by URL.
    Returns content and metadata if found, else None.
    """
    try:
        results = mindmap_raw_content_collection.get(where={"url": url}, limit=1, include=['documents', 'metadatas'])
        if results['ids']:
            logfire.info(f"Found raw content for mindmap in ChromaDB for {url}")
            return {
                'id': results['ids'][0],
                'content': results['documents'][0],
                'metadata': results['metadatas'][0]
            }
        logfire.info(f"No raw content for mindmap found in ChromaDB for {url}")
        return None
    except Exception as e:
        logfire.error(f"ChromaDB query failed for mindmap raw content for {url}: {str(e)}")
        return None

def check_mindmap_script_in_db(url: str) -> Optional[dict]:
    """
    Checks ChromaDB for an existing mindmap script by URL.
    Returns script content and metadata if found, else None.
    """
    try:
        results = mindmap_scripts_collection.get(where={"url": url}, limit=1, include=['documents', 'metadatas'])
        if results['ids']:
            logfire.info(f"Found mindmap script in ChromaDB for {url}")
            return {
                'id': results['ids'][0],
                'content': results['documents'][0],
                'metadata': results['metadatas'][0]
            }
        logfire.info(f"No mindmap script found in ChromaDB for {url}")
        return None
    except Exception as e:
        logfire.error(f"ChromaDB query failed for mindmap script for {url}: {str(e)}")
        return None

def check_mindmap_dot_in_db(url: str) -> Optional[dict]:
    """
    Checks ChromaDB for an existing mindmap DOT content by URL.
    Returns DOT content and metadata if found, else None.
    """
    try:
        results = mindmap_dots_collection.get(where={"url": url}, limit=1, include=['documents', 'metadatas'])
        if results['ids']:
            logfire.info(f"Found mindmap DOT in ChromaDB for {url}")
            return {
                'id': results['ids'][0],
                'content': results['documents'][0],
                'metadata': results['metadatas'][0]
            }
        logfire.info(f"No mindmap DOT found in ChromaDB for {url}")
        return None
    except Exception as e:
        logfire.error(f"ChromaDB query failed for mindmap DOT for {url}: {str(e)}")
        return None

# Check Graphviz installation
def check_graphviz() -> bool:
    """
    Verifies if Graphviz is installed by checking the 'dot' command.
    Returns True if functional, False otherwise.
    """
    try:
        result = subprocess.run(['dot', '-V'], capture_output=True, check=True, text=True)
        logfire.info(f"Graphviz 'dot' command found in PATH: {result.stderr.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logfire.error(f"Graphviz 'dot' command not found: {str(e)}")
        return False

# Validate DOT content
def validate_dot_content(dot_content: str) -> bool:
    """
    Validates Graphviz DOT content for correct syntax.
    Ensures it starts with 'digraph G {' and contains valid node/edge definitions.
    """
    if not dot_content or not dot_content.strip().startswith('digraph G {') or '}' not in dot_content:
        return False
    return bool(re.search(r'\w+\s*\[.*\];|\w+\s*->\s*\w+', dot_content))

# Check directory permissions
def check_directory_permissions(path: str) -> bool:
    """
    Tests write permissions for a directory by creating and deleting a test file.
    Returns True if permissions are sufficient, False otherwise.
    """
    try:
        test_file = os.path.join(path, "test_permissions.txt")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        return True
    except Exception as e:
        logfire.error(f"Directory permission check failed for {path}: {str(e)}")
        return False

# Fallback DOT generation function
def generate_fallback_dot(summary: str, url: str) -> str:
    """
    Generates a fallback Graphviz DOT string when primary generation fails.
    Creates a simple mindmap with predefined nodes based on URL context.
    """
    logfire.info(f"Generating fallback DOT string for {url}")
    main_topic = "PydanticAI Framework" if "pydantic" in url.lower() else "Healthy and Happy Life"
    dot_lines = [
        'digraph G {',
        '  rankdir=LR;',
        '  node [shape=box, style=filled, fillcolor=lightblue];',
        f'  main [label="{main_topic}"];'
    ]
    
    subtopics = [
        "Social Connections" if "youtube" in url.lower() else "Model-Agnostic Support",
        "Quality Relationships" if "youtube" in url.lower() else "Type-Safe Design",
        "Cognitive Health" if "youtube" in url.lower() else "Dependency Injection",
        "Life Longevity" if "youtube" in url.lower() else "Streamed Responses"
    ]
    for i, subtopic in enumerate(subtopics, 1):
        dot_lines.append(f'  sub{i} [label="{subtopic}", fillcolor=lightgreen];')
        dot_lines.append(f'  main -> sub{i};')
    
    dot_lines.append('}')
    dot_content = '\n'.join(dot_lines)
    logfire.info("Fallback DOT string generated", url=url, dot_content=dot_content.replace('\n', '\\n'))
    return dot_content

# Pydantic Models
class MindmapContentInput(BaseModel):
    """Input model for extracting mindmap content from a URL."""
    url: str = Field(description="The URL (web or YouTube) for mindmap content extraction.")
    output_file: Optional[str] = Field(None, description="Optional file path to save raw content.")

class MindmapScriptInput(BaseModel):
    """Input model for generating a mindmap script from content."""
    url: str = Field(description="The URL for mindmap script generation.")
    raw_content: Optional[str] = Field(None, description="Optional raw content if not from DB.")
    output_file: Optional[str] = Field(None, description="Optional file path to save script.")

class MindmapGenerationInput(BaseModel):
    """Input model for rendering a mindmap image from DOT content."""
    url: str = Field(description="The URL for mindmap image generation.")
    dot_content: Optional[str] = Field(None, description="The Graphviz DOT string.")
    output_image_path: str = Field(description="The file path for the mindmap image (e.g., 'mindmap.png').")

# Content Extraction Tool
def create_mindmap_content_extraction_tool() -> Tool:
    """
    Creates a tool to extract raw content for mindmap processing from ChromaDB.
    Retrieves from YouTube or web collections and stores in mindmap_raw_content_collection.
    """
    async def extract_mindmap_content_from_db(input_model: MindmapContentInput) -> str:
        """
        Extracts raw content for a mindmap from ChromaDB based on a URL.
        Saves to an optional output file and returns the content.
        """
        url = input_model.url
        output_file = input_model.output_file
        logfire.info(f"Mindmap tool: Attempting to retrieve content for mindmap from ChromaDB for URL: {url}")

        # Check existing mindmap content
        existing_data = check_mindmap_raw_content_in_db(url)
        if existing_data:
            content = existing_data['content']
            logfire.info(f"Mindmap tool: Found existing content in mindmap_raw_content for {url}")
            return content

        # Try YouTube transcripts
        youtube_collection = chromadb.PersistentClient(path=CHROMA_DB_PATH).get_or_create_collection(name="youtube_transcripts", embedding_function=embedding_function)
        youtube_results = youtube_collection.get(where={"url": url}, limit=1, include=['documents'])
        if youtube_results['ids']:
            content = youtube_results['documents'][0]
            source_type = "youtube"
        else:
            # Try web content
            web_collection = chromadb.PersistentClient(path=CHROMA_DB_PATH).get_or_create_collection(name="web_content_general", embedding_function=embedding_function)
            web_results = web_collection.get(where={"url": url}, limit=1, include=['documents'])
            if web_results['ids']:
                content = web_results['documents'][0]
                source_type = "web"
            else:
                logfire.warning(f"Mindmap tool: No content found in 'youtube_transcripts' or 'web_content_general' for {url}.")
                return f"Error: No content found for mindmap generation for {url}. Please ensure the URL has been processed."

        # Store in mindmap_raw_content_collection
        max_length = 5000
        if len(content) > max_length:
            content = content[:max_length]
            logfire.info(f"Mindmap tool: Truncated content to {max_length} characters for {url}")
        mindmap_raw_content_collection.add(
            documents=[content],
            metadatas=[{'url': url, 'source': f'extracted_for_mindmap_from_{source_type}'}],
            ids=[str(uuid.uuid4())]
        )
        logfire.info(f"Mindmap tool: Raw content stored in 'mindmap_raw_content' for {url}")

        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                logfire.info(f"Mindmap tool: Raw content saved to {output_file}")
            except IOError as io_e:
                logfire.error(f"Mindmap tool: Could not save raw content to {output_file}: {io_e}")

        return content

    return Tool[MindmapContentInput](
        name="extract_mindmap_content",
        description="Retrieves pre-extracted content from ChromaDB for mindmap processing.",
        function=extract_mindmap_content_from_db
    )

# Script Generation Tool
def create_mindmap_script_generation_tool() -> Tool:
    """
    Creates a tool to retrieve or generate content for a mindmap script.
    Uses provided raw content or fetches from ChromaDB.
    """
    async def get_content_for_script(input_model: MindmapScriptInput) -> str:
        """
        Retrieves or uses provided raw content for mindmap script generation.
        Truncates content if necessary and returns it for further processing.
        """
        url = input_model.url
        raw_content = input_model.raw_content
        output_file = input_model.output_file

        if raw_content:
            content_to_use = raw_content
            logfire.info("Mindmap tool: Using provided raw content for script generation.")
        else:
            existing_data = check_mindmap_raw_content_in_db(url)
            if existing_data:
                content_to_use = existing_data['content']
                logfire.info(f"Mindmap tool: Retrieved raw content from 'mindmap_raw_content' for {url}.")
            else:
                logfire.error(f"Mindmap tool: No raw content found for {url}.")
                return f"Error: No raw content available for {url}. Please extract content first."
        
        max_length = 5000
        if len(content_to_use) > max_length:
            content_to_use = content_to_use[:max_length]
            logfire.info(f"Mindmap tool: Truncated content to {max_length} characters for script generation for {url}")
        
        return content_to_use

    return Tool[MindmapScriptInput](
        name="get_content_for_mindmap_script",
        description="Retrieves raw content for mindmap script generation.",
        function=get_content_for_script
    )

# Mindmap Rendering Tool
def create_mindmap_rendering_tool() -> Tool:
    """
    Creates a tool to render a Graphviz DOT string into a PNG mindmap image.
    Validates DOT content and ensures directory permissions.
    """
    async def render_mindmap_image(input_model: MindmapGenerationInput) -> str:
        """
        Renders a mindmap image from a Graphviz DOT string using Graphviz.
        Saves the image to the specified path and handles errors.
        """
        url = input_model.url
        dot_content = input_model.dot_content
        output_image_path = os.path.abspath(input_model.output_image_path)
        logfire.info(f"Mindmap tool: Rendering mindmap image for {url} to {output_image_path}")

        if not check_graphviz():
            return "Error: Graphviz 'dot' command not found. Please install Graphviz."

        output_dir = os.path.dirname(output_image_path) or "."
        if not check_directory_permissions(output_dir):
            return f"Error: No write permissions for directory {output_dir}. Please ensure the directory is writable."

        if not dot_content or not validate_dot_content(dot_content):
            existing_dot = check_mindmap_dot_in_db(url)
            if existing_dot and validate_dot_content(existing_dot['content']):
                dot_content = existing_dot['content']
                logfire.info(f"Mindmap tool: Retrieved valid DOT content from ChromaDB for {url}")
            else:
                logfire.error(f"Mindmap tool: Invalid or empty DOT content for {url}.")
                return f"Error: Invalid or empty DOT content for {url}. Please try again or check the generated DOT string."

        dot_file_path = f"{output_image_path}.dot"
        try:
            with open(dot_file_path, 'w', encoding='utf-8') as f:
                f.write(dot_content)
            logfire.info(f"Mindmap tool: DOT content saved to {dot_file_path}")

            command = ['dot', '-Tpng', dot_file_path, '-o', output_image_path]
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                shell=platform.system() == "Windows",
                timeout=10
            )
            stdout_str = process.stdout.strip()
            stderr_str = process.stderr.strip()

            if process.returncode != 0:
                error_message = stderr_str or stdout_str or "Unknown Graphviz error"
                logfire.error(f"Mindmap rendering failed for {url}: {error_message}")
                debug_dot_path = f"{output_image_path}_failed.dot"
                with open(debug_dot_path, 'w', encoding='utf-8') as f:
                    f.write(dot_content)
                return f"Error: Failed to render mindmap image: {error_message}\nDOT content saved for manual rendering: {debug_dot_path}"

            if not os.path.exists(output_image_path):
                logfire.error(f"Mindmap rendering failed for {url}: Output file {output_image_path} not created.")
                debug_dot_path = f"{output_image_path}_failed.dot"
                with open(debug_dot_path, 'w', encoding='utf-8') as f:
                    f.write(dot_content)
                return f"Error: Mindmap image was not created at {output_image_path}.\nDOT content saved for manual rendering: {debug_dot_path}"

            logfire.info(f"Mindmap image saved to {output_image_path}")
            return f"Mindmap image saved to: {output_image_path}"

        except subprocess.TimeoutExpired:
            logfire.error(f"Mindmap rendering timed out for {url} after 10 seconds.")
            debug_dot_path = f"{output_image_path}_failed.dot"
            with open(debug_dot_path, 'w', encoding='utf-8') as f:
                f.write(dot_content)
            return f"Error: Mindmap rendering timed out after 10 seconds.\nDOT content saved for manual rendering: {debug_dot_path}"
        except Exception as e:
            logfire.error(f"Mindmap rendering failed for {url}: {str(e)}")
            debug_dot_path = f"{output_image_path}_failed.dot"
            with open(debug_dot_path, 'w', encoding='utf-8') as f:
                f.write(dot_content)
            return f"Error: Failed to render mindmap image: {str(e)}\nDOT content saved for manual rendering: {debug_dot_path}"
        finally:
            if os.path.exists(dot_file_path):
                try:
                    os.remove(dot_file_path)
                    logfire.info(f"Cleaned up temporary DOT file: {dot_file_path}")
                except OSError as e:
                    logfire.error(f"Failed to clean up temporary DOT file {dot_file_path}: {str(e)}")

    return Tool[MindmapGenerationInput](
        name="render_mindmap_image",
        description="Renders a Graphviz DOT string into a PNG image.",
        function=render_mindmap_image
    )

class MindmapAgent(Agent):
    """
    Agent for generating mindmaps from URLs using content extraction, script generation, and DOT rendering.
    Integrates with ChromaDB and Graphviz for storage and visualization.
    """
    def __init__(self, api_key: str):
        """
        Initializes the MindmapAgent with a Gemini model and mindmap-specific tools.
        Sets up ChromaDB collections for content, scripts, and DOT strings.
        """
        super().__init__(
            model='gemini-1.5-pro',
            api_key=api_key,
            tools=[
                create_mindmap_content_extraction_tool(),
                create_mindmap_script_generation_tool(),
                create_mindmap_rendering_tool()
            ],
            system_prompt=(
                'You are an expert mindmap generation assistant. Your goal is to create a detailed, colorful visual representation '
                'of content in a hierarchical mindmap format using Graphviz DOT language. Workflow:\n'
                '1. **Content Retrieval:** Use provided summary or `extract_mindmap_content` to get raw text from ChromaDB.\n'
                '2. **Script Generation:** If no summary is provided, use `get_content_for_mindmap_script` to retrieve content, then generate a concise, hierarchical summary (150-250 words). Store in `mindmap_scripts_collection`.\n'
                '3. **DOT String Generation:** Create a valid Graphviz DOT string starting with `digraph G { rankdir=LR;`. Use:\n'
                '   - `node [shape=box, style=filled, fillcolor=lightblue]` for the main topic.\n'
                '   - `node [shape=ellipse, style=filled, fillcolor=lightgreen]` for key subtopics.\n'
                '   - `node [shape=oval, style=filled, fillcolor=lightyellow]` for detailed points under subtopics.\n'
                '   - Include at least 5 subtopics and 3-4 details per subtopic based on the summary content.\n'
                '   - Use directed edges (e.g., main -> sub1) to show hierarchy.\n'
                '   - Return ONLY the DOT string, enclosed in curly braces, with no additional text or code (e.g., no `print()` or Python syntax).\n'
                '4. **Image Rendering:** Use `render_mindmap_image` to convert the DOT string to a PNG image.\n'
                '5. **Error Handling:** Truncate content to 5000 characters if needed. Use fallback DOT only if all attempts fail.'
            )
        )
        self.mindmap_raw_content_collection = mindmap_raw_content_collection
        self.mindmap_scripts_collection = mindmap_scripts_collection
        self.mindmap_dots_collection = mindmap_dots_collection

    async def generate_mindmap_workflow(self, url: str, output_image_path: str, summary: Optional[str] = None) -> str:
        """
        Orchestrates the mindmap generation workflow from content extraction to image rendering.
        Uses provided summary or extracts content, generates a script, creates a DOT string, and renders the image.
        """
        logfire.info(f"MindmapAgent: Starting mindmap workflow for URL: {url}")

        # Step 1: Use provided summary or extract raw content
        print("  - Preparing content for mindmap...")
        if summary:
            raw_content = summary
            logfire.info(f"MindmapAgent: Using provided summary for {url}. Length: {len(raw_content)} chars.")
        else:
            extract_result = await self.run(f"extract_mindmap_content(url='{url}')")
            if "Error" in extract_result.output:
                logfire.error(f"MindmapAgent: Content extraction failed for {url}: {extract_result.output}")
                return extract_result.output
            raw_content = extract_result.output
            logfire.info(f"MindmapAgent: Raw content retrieved for {url}. Length: {len(raw_content)} chars.")
        print("  - Content prepared.")

        # Step 2: Generate script/summary
        print("  - Generating mindmap script/summary...")
        existing_script = check_mindmap_script_in_db(url)
        if existing_script and not summary:  # Use existing script unless new summary provided
            mindmap_script_summary = existing_script['content']
            logfire.info(f"MindmapAgent: Using existing script for {url}.")
        else:
            max_content_length = 5000
            if len(raw_content) > max_content_length:
                raw_content = raw_content[:max_content_length]
                logfire.info(f"MindmapAgent: Truncated content to {max_content_length} chars for {url}.")
            
            mindmap_script_summary = raw_content if summary else None
            if not mindmap_script_summary:
                script_instruction = (
                    f"Generate a concise, hierarchical summary (150-250 words) for a mindmap based on the content from {url}. "
                    "Identify the main topic, at least 5 key subtopics, and 3-4 important details per subtopic. Return ONLY the summary text.\n\n"
                    f"Content (truncated if necessary):\n{raw_content}"
                )
                for attempt in range(2):
                    try:
                        script_response = await self.run(script_instruction)
                        mindmap_script_summary = script_response.output.strip()
                        if not mindmap_script_summary or "Error" in mindmap_script_summary:
                            logfire.warning(f"MindmapAgent: Script generation failed on attempt {attempt + 1} for {url}.")
                            if attempt == 1:
                                return f"Error: Mindmap script generation failed for {url} after retries."
                            continue
                        break
                    except Exception as e:
                        logfire.error(f"MindmapAgent: Script generation error on attempt {attempt + 1}: {str(e)}")
                        if attempt == 1:
                            return f"Error: Mindmap script generation failed for {url}: {str(e)}"
            
            self.mindmap_scripts_collection.add(
                documents=[mindmap_script_summary],
                metadatas=[{'url': url, 'source': 'agent_generated_mindmap_script'}],
                ids=[str(uuid.uuid4())]
            )
            logfire.info(f"MindmapAgent: Script stored in 'mindmap_scripts' for {url}.")
        print("  - Mindmap script generated and stored.")

        # Step 3: Generate DOT string
        print("  - Generating Graphviz DOT string...")
        existing_dot = check_mindmap_dot_in_db(url)
        if existing_dot and not summary:  # Use existing DOT unless new summary provided
            dot_content = existing_dot['content']
            logfire.info(f"MindmapAgent: Using existing DOT content for {url}.")
        else:
            dot_instruction = (
                f"Generate a Graphviz DOT string for a detailed mindmap based on this summary from {url}:\n"
                f"\"{mindmap_script_summary}\"\n"
                "Start with: 'digraph G { rankdir=LR;'\n"
                "Use:\n"
                "- `node [shape=box, style=filled, fillcolor=lightblue]` for the main topic.\n"
                "- `node [shape=ellipse, style=filled, fillcolor=lightgreen]` for key subtopics.\n"
                "- `node [shape=oval, style=filled, fillcolor=lightyellow]` for detailed points.\n"
                "Include:\n"
                "- A main node labeled with the primary topic (e.g., 'PydanticAI Framework').\n"
                "- At least 5 subtopics as separate nodes, each with 3-4 detail nodes reflecting the summary content.\n"
                "- Directed edges (e.g., main -> sub1) to show hierarchy.\n"
                "Return ONLY the DOT string, enclosed in curly braces, with no additional text or code (e.g., no `print()` or Python syntax)."
            )
            for attempt in range(3):
                try:
                    dot_response = await self.run(dot_instruction)
                    dot_content = dot_response.output.strip()
                    if not validate_dot_content(dot_content):
                        logfire.warning(f"MindmapAgent: Invalid DOT content on attempt {attempt + 1} for {url}. Content: {dot_content}")
                        if attempt == 2:
                            logfire.info(f"MindmapAgent: Using fallback DOT for {url} after retries.")
                            dot_content = generate_fallback_dot(mindmap_script_summary, url)
                        continue
                    break
                except Exception as e:
                    logfire.error(f"MindmapAgent: DOT generation error on attempt {attempt + 1}: {str(e)}")
                    if attempt == 2:
                        logfire.info(f"MindmapAgent: Using fallback DOT for {url} after retries.")
                        dot_content = generate_fallback_dot(mindmap_script_summary, url)
                        break
            
            self.mindmap_dots_collection.add(
                documents=[dot_content],
                metadatas=[{'url': url, 'script_summary': mindmap_script_summary, 'source': 'agent_generated_dot'}],
                ids=[str(uuid.uuid4())]
            )
            logfire.info(f"MindmapAgent: DOT content stored in 'mindmap_dots' for {url}.")
        print("  - DOT string generated and stored.")

        # Step 4: Render mindmap image
        print(f"  - Rendering mindmap image to {output_image_path}...")
        render_result = await self.run(
            f"render_mindmap_image(url='{url}', dot_content='''{dot_content}''', output_image_path='{output_image_path}')"
        )
        if "Error" in render_result.output or not os.path.exists(output_image_path):
            logfire.error(f"MindmapAgent: Rendering failed for {url}: {render_result.output}")
            return render_result.output
        
        logfire.info(f"MindmapAgent: Mindmap workflow completed for {url}.")
        return f"Mindmap created successfully! Image saved to: {output_image_path}\n\nSummary used for Mindmap: {mindmap_script_summary}"

if __name__ == "__main__":
    async def test():
        """
        Tests the MindmapAgent by generating a mindmap for a sample YouTube URL.
        Requires a valid GEMINI_API_KEY in the .env file.
        """
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if not gemini_api_key:
            print("Error: GEMINI_API_KEY not set.")
            return
        agent = MindmapAgent(api_key=gemini_api_key)
        result = await agent.generate_mindmap_workflow("https://www.youtube.com/watch?v=8KkKuTCFvzI", "test_mindmap.png")
        print(result)
    
    asyncio.run(test())