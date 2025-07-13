import argparse
import os
import asyncio
import uuid
import platform
from urllib.parse import urlparse
from typing import Optional, Tuple, List
from datetime import datetime
from dotenv import load_dotenv
import logfire
from pydantic import BaseModel, Field
from pydantic_ai import Agent, Tool
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider
import subprocess
import chromadb
from chromadb.utils import embedding_functions
import json

from youtube import YouTubeAgent, get_youtube_video_id, check_youtube_transcript_in_db
from web import WebAgent, check_web_content_in_db
from mindmap import MindmapAgent, check_graphviz, check_mindmap_raw_content_in_db
from podcast import create_script_generation_tool, create_audio_generation_tool, AudioInput
from Pdf import validate_pdf_file, create_pdf_extraction_tool, create_pdf_query_tool, PDFAgent
from image import ImageAgent, create_image_analysis_tool, create_image_query_tool, validate_image_file, initialize_metadata

load_dotenv()

logfire_token = os.getenv('LOGFIRE_TOKEN')
if not logfire_token:
    print("Error: LOGFIRE_TOKEN not set in .env file.")
    exit(1)
logfire.configure(token=logfire_token)
logfire.info("Starting main.py - Multi-Agent Planner with Chatbot Interface")

# Initialize image metadata file
initialize_metadata()

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

CHROMA_DB_PATH = "./chroma_db"
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
context_collection = chroma_client.get_or_create_collection(
    name="planner_context", embedding_function=embedding_functions.DefaultEmbeddingFunction()
)
## check graphiz tool for mindmap
def test_graphviz():
    try:
        with open("test.dot", "w", encoding="utf-8") as f:
            f.write('digraph G { rankdir=LR; main [label="Test"]; main -> sub1; }')
        result = subprocess.run(
            ['dot', '-Tpng', 'test.dot', '-o', 'test.png'],
            capture_output=True,
            text=True,
            shell=platform.system() == "Windows",
            timeout=10
        )
        if result.returncode == 0 and os.path.exists("test.png"):
            logfire.info("Graphviz test successful: test.png created.")
            os.remove("test.png")
            os.remove("test.dot")
            return True
        else:
            logfire.error(f"Graphviz test failed: {result.stderr or 'No error message'}")
            return False
    except subprocess.TimeoutExpired:
        logfire.error("Graphviz test timed out after 10 seconds.")
        return False
    except Exception as e:
        logfire.error("Graphviz test failed", exc_info=e)
        return False
    finally:
        if os.path.exists("test.dot"):
            os.remove("test.dot")
        if os.path.exists("test.png"):
            os.remove("test.png")

if not test_graphviz():
    print("Warning: Graphviz test failed. Mindmap rendering may not work.")

## ffmeg for podcast file
ffmpeg_path = os.getenv('FFMPEG_PATH', 'C:\\Users\\tript\\Downloads\\ffmpeg-7.1.1-essentials_build\\bin')
if ffmpeg_path and os.path.exists(ffmpeg_path):
    os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg_path)
    logfire.info(f"FFMPEG configured at {ffmpeg_path}")
else:
    logfire.warning("FFMPEG_PATH not set or invalid. Audio processing may fail.")

## check url type web, youtube, image or pdf
class URLTypeDetectorInput(BaseModel):
    url: str = Field(description="The URL to determine the type (YouTube or Web).")

def create_url_type_detector_tool() -> Tool:
    async def detect_url_type(input_model: URLTypeDetectorInput) -> str:
        url = input_model.url.strip().lower()
        if "youtube.com/watch" in url or "youtu.be/" in url:
            return "youtube"
        return "web"
    
    return Tool[URLTypeDetectorInput](
        name="detect_url_type",
        description="Determines if a URL is YouTube or web. Returns exactly 'youtube' or 'web' to ensure compatibility with content extraction logic.",
        function=detect_url_type
    )

async def _extract_topic(resource: str, resource_type: str, planner: Agent) -> str:
    try:
        # First, check if topic exists in ChromaDB for this resource
        results = context_collection.get(
            where={'resource': resource},
            include=['metadatas']
        )
        if results['ids']:
            topic = results['metadatas'][0].get('topic', 'General')
            logfire.info(f"Reused existing topic for {resource}: {topic}")
            return topic

        # Try agent-based topic extraction
        input_text = f"Resource: {resource}\nType: {resource_type}\nGenerate a concise topic name (2-5 words) based on the resource URL or file path."
        response = await planner.run(input_text)
        topic = await _extract_response_content(response)
        
        # Clean and validate topic
        topic = topic.strip().title()
        if not topic or len(topic.split()) > 5:
            raise ValueError("Invalid topic generated by agent")
        
        logfire.info(f"Extracted topic for {resource}: {topic}")
        return topic
    except Exception as e:
        logfire.error("Failed to extract topic for {resource}", resource=resource, exc_info=e)
        
        try:
            if resource_type in ["web", "youtube"]:
                parsed_url = urlparse(resource)
                domain = parsed_url.netloc.replace("www.", "").split(".")[0].title()
                path = parsed_url.path.strip("/").replace("_", " ").title()
                topic = path.split("/")[-1] if path else domain
            elif resource_type == "pdf":
                filename = os.path.basename(resource).lower().replace(".pdf", "").replace("_", " ").title()
                topic = filename
            elif resource_type == "image":
                filename = os.path.basename(resource).lower().replace(".jpg", "").replace(".jpeg", "").replace(".png", "").replace("_", " ").title()
                topic = filename
            else:
                topic = "General"
            logfire.info(f"Topic for {resource}: {topic}")
            return topic
        except Exception as e2:
            logfire.error("Topic extraction failed for {resource}", resource=resource, exc_info=e2)
            return "General"

def _load_context():
    try:
        results = context_collection.get(include=['metadatas'])
        if results['ids']:
            topics = set(meta.get('topic', 'Unknown') for meta in results['metadatas'])
            logfire.info(f"Available topics in ChromaDB: {', '.join(topics)}")
    except Exception as e:
        logfire.error("Failed to load context", exc_info=e)

async def _save_context(resource: str, resource_type: str, summary: str, planner: Agent):
    try:
        topic = await _extract_topic(resource, resource_type, planner)
        unique_id = str(uuid.uuid4())
        context_collection.upsert(
            documents=[summary],
            metadatas=[{
                'resource': resource,
                'resource_type': resource_type,
                'topic': topic
            }],
            ids=[f"context_{unique_id}"]
        )
        logfire.info(f"Saved context: resource={resource}, type={resource_type}, topic={topic}, id=context_{unique_id}")
    except Exception as e:
        logfire.error("Failed to save context for {resource}", resource=resource, exc_info=e)

async def _query_chroma_db(query_text: str, planner: Agent) -> str:
    try:
        # First, try exact topic match
        topic_query = query_text.replace("short description of ", "").strip().title()
        results = context_collection.get(
            where={'topic': topic_query},
            include=['documents', 'metadatas']
        )
        
        if results['ids']:
            top_doc = results['documents'][0]
            top_meta = results['metadatas'][0]
            resource = top_meta.get('resource', 'Unknown')
            resource_type = top_meta.get('resource_type', 'Unknown')
            topic = top_meta.get('topic', 'Unknown')
            logfire.info(f"Found exact topic match for query '{query_text}': resource={resource}, type={resource_type}, topic={topic}")
            
            # Generate concise answer
            prompt = f"Based on the following content, provide a concise summary or answer (50-100 words) for: {query_text}\n\nContent:\n{top_doc}"
            response = await planner.run(prompt)
            answer = await _extract_response_content(response)
            return answer
        
      
        results = context_collection.query(
            query_texts=[query_text],
            n_results=5,
            include=['documents', 'metadatas', 'distances']
        )
        
        if not results['ids'] or not results['ids'][0]:
            logfire.info(f"No relevant content found in ChromaDB for query: {query_text}")
            return f"No relevant content found in database for '{query_text}'. Please provide a specific URL, PDF, or image path to generate new content."

        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results['distances'][0]
        
        relevant_docs = [(doc, meta, dist) for doc, meta, dist in zip(documents, metadatas, distances)]
        relevant_docs.sort(key=lambda x: x[2])
        
        top_doc, top_meta = relevant_docs[0][0], relevant_docs[0][1]
        resource = top_meta.get('resource', 'Unknown')
        resource_type = top_meta.get('resource_type', 'Unknown')
        topic = top_meta.get('topic', 'Unknown')
        
        logfire.info(f"Found relevant document for query '{query_text}': resource={resource}, type={resource_type}, topic={topic}")
        
        prompt = f"Based on the following content, provide a concise summary or answer (50-100 words) for: {query_text}\n\nContent:\n{top_doc}"
        response = await planner.run(prompt)
        answer = await _extract_response_content(response)
        return answer
    except Exception as e:
        logfire.error("ChromaDB query error for {query}", query=query_text, exc_info=e)
        return f"Error: Failed to query database for '{query_text}': {str(e)}"

# Create standalone PlannerAgent as an Agent instance
def create_planner_agent(gemini_api_key: str):
    tools = [
        create_url_type_detector_tool(),
        create_image_analysis_tool(),
        create_image_query_tool(),
        create_pdf_extraction_tool(),
        create_pdf_query_tool(),
    ]
    return Agent(
        model=GeminiModel('gemini-1.5-flash', provider=GoogleGLAProvider(api_key=gemini_api_key)),
        api_key=gemini_api_key,
        tools=tools,
        system_prompt=(
            'You are an expert multi-agent content planner coordinating web, YouTube, image, PDF, and mindmap generation tasks. '
            'Your role is to parse user requests, identify resource types (web, YouTube, image, PDF, or mindmap), and delegate tasks to specialized agents. '
            'Handle the following tasks accurately: '
            '- **Web/YouTube Summarization**: Summarize web pages or YouTube videos (150-250 words) using stored content in ChromaDB. '
            '- **Web/YouTube Questions**: Answer questions about web or YouTube content using stored data or summaries. '
            '- **Image Analysis**: Analyze images (local paths or URLs) to provide a 100-150 word description, stored in image_metadata.json and ChromaDB. '
            '- **Image Questions**: Answer questions about images based on stored descriptions, including queries like "what is this image about". '
            '- **PDF Summarization**: Summarize PDFs (150-250 words) using stored content in ChromaDB and save in pdf_metadata.json. '
            '- **PDF Questions**: Answer questions about PDFs based on stored content in ChromaDB. '
            '- **Mindmap Generation**: Generate a mindmap image for web/YouTube URLs, PDFs, or previous summaries using Graphviz, saving to a PNG file. '
            '- **General Questions**: Answer questions by searching all relevant content in ChromaDB using exact topic matches or embedding similarity, without requiring a specific resource. '
            '- **Topic Extraction**: Generate concise topic names (2-5 words) for resources based on their content, URL, or filename. '
            '- **Error Handling**: Provide clear error messages for invalid inputs, missing resources, or API issues (e.g., 429/503 errors). '
            'Use only verified data, avoid assumptions, and ensure responses are concise and accurate. '
            'Store all summaries and descriptions in ChromaDB with resource, resource_type, and topic metadata for context.'
        )
    )

async def _extract_response_content(response) -> str:
    try:
        if hasattr(response, 'output'):
            output = response.output
            if isinstance(output, dict):
                for key in ['summary', 'content', 'text', 'output', 'message', 'description']:
                    if key in output and isinstance(output[key], str):
                        return output[key]
                return str(output.get('summary', output.get('description', str(output))))
            elif isinstance(output, str):
                return output
            else:
                return str(output)
        return str(response)
    except Exception as e:
        logfire.error("Failed to extract response content", exc_info=e)
        return f"Error: Failed to extract content: {str(e)}"

async def _ensure_content(planner: Agent, url: str) -> Tuple[Optional[str], Optional[str]]:
    logfire.info(f"Checking URL type for: {url}")
    print(f"Checking URL type for: {url}...")
    try:
        url_type_response = await planner.run(f"detect_url_type(url='{url}')")
        raw_output = await _extract_response_content(url_type_response)
        current_url_type = raw_output.lower()
        if 'youtube' in current_url_type:
            current_url_type = "youtube"
        elif 'web' in current_url_type:
            current_url_type = "web"
        else:
            logfire.error(f"Invalid URL type detected: {raw_output}")
            return f"Error: Invalid URL type: {raw_output}", None
        print(f"Detected URL type: {current_url_type.capitalize()}")

        extracted_content = None
        if current_url_type == "youtube":
            existing_data = check_youtube_transcript_in_db(url)
            if existing_data:
                print("YouTube transcript found in database.")
                extracted_content = existing_data['content']
            else:
                print(f"Extracting transcript from {url}...")
                extract_response = await youtube_agent.run(f"get_youtube_transcript(youtube_url='{url}')")
                extracted_content = await _extract_response_content(extract_response)
                if "Error" in extracted_content:
                    logfire.error(f"YouTube transcript extraction failed: {extracted_content}")
                    return extracted_content, None
                print("Transcript extracted and stored.")
        elif current_url_type == "web":
            existing_data = check_web_content_in_db(url)
            if existing_data:
                print("Web content found in database.")
                extracted_content = existing_data['content']
            else:
                print(f"Extracting content from {url}...")
                extract_response = await web_agent.run(f"extract_web_content(web_url='{url}')")
                extracted_content = await _extract_response_content(extract_response)
                if "Error" in extracted_content:
                    logfire.error(f"Web content extraction failed: {extracted_content}")
                    return extracted_content, None
                print("Web content extracted and stored.")
        
        await _save_context(url, current_url_type, extracted_content, planner)
        return extracted_content, current_url_type
    except Exception as e:
        logfire.error("Error in content extraction for {url}", url=url, exc_info=e)
        return f"Error: Failed to extract content for {url}: {str(e)}", None

async def run_task(planner: Agent, user_request: str) -> str:
    logfire.info(f"Processing request: {user_request}")
    response_parts: List[str] = []

    user_request = user_request.replace('podacst', 'podcast', 1).lower()
    # Detect URL, PDF, or image with minimal string checks
    url = None
    pdf_path = None
    image_path = None
    if 'http://' in user_request or 'https://' in user_request:
        for word in user_request.split():
            if word.startswith('http'):
                url = word.strip('"')
                break
    elif '.pdf' in user_request:
        for word in user_request.split():
            if word.endswith('.pdf'):
                pdf_path = word
                break
    elif any(ext in user_request for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']):
        for word in user_request.split():
            if any(word.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']) or \
               any(word.startswith('http') and ext in word for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']):
                image_path = word.strip('"')
                break

    request_lower = user_request.lower()
    wants_summary = "summary" in request_lower or "short description" in request_lower
    wants_description = any(kw in request_lower for kw in ["describe", "what is the image about"])
    wants_mindmap = any(kw in request_lower for kw in ["mindmap", "create a mindmap"])
    is_podcast = "create podcast" in request_lower
    is_question = any(kw in request_lower for kw in ["what is", "color of", "background", "setting", "describe", "example", "usage", "summary", "short description"]) and not (url or pdf_path or image_path)

    # Load context to check available topics
    _load_context()

    if image_path:
        print(f"\nProcessing Image: {image_path}")
        is_url = image_path.startswith('http')
        if not is_url and not validate_image_file(image_path):
            response_parts.append(f"Error: Invalid image file: {image_path}. Ensure the file exists, is a valid image, or provide a publicly accessible URL (e.g., via Imgur).")
            return "\n".join(response_parts)

        if not wants_description and not wants_mindmap and not is_podcast and not is_question:
            response_parts.append(f"Image prepared for {image_path}. Choose an action: 'describe', 'create mindmap', 'create podcast', or ask a question (e.g., 'color of dog').")
            return "\n".join(response_parts)

        description_output = None
        if wants_description or wants_summary or is_podcast or wants_mindmap or is_question:
            print(f"\nGenerating Description for Image: {image_path}")
            try:
                description_response = await image_agent.run(
                    f"analyze_image(image_path='{image_path}')"
                )
                description_output = await _extract_response_content(description_response)
                if "Error" in description_output:
                    logfire.error(f"Image description failed: {description_output}")
                    response_parts.append(f"Error: Unable to analyze {image_path}. Ensure the file is valid or upload to Imgur and provide the URL.")
                else:
                    if wants_description or wants_summary:
                        response_parts.append(f"\nDescription for {image_path}")
                        response_parts.append(description_output)
                    await _save_context(image_path, "image", description_output, planner)
                    logfire.info(f"Description generated for {image_path}")
            except Exception as e:
                logfire.error("Image processing error for {image_path}", image_path=image_path, exc_info=e)
                response_parts.append(f"Error: Failed to process image {image_path}: {str(e)}. Ensure the file is valid or try using a URL.")

            if is_question and not (wants_description or wants_summary):
                print(f"\nAnswering question for {image_path}: {user_request}")
                try:
                    query_response = await image_agent.run(
                        f"query_image_content(image_path='{image_path}', question='{user_request}')"
                    )
                    query_output = await _extract_response_content(query_response)
                    if "Error" in query_output:
                        response_parts.append(f"Error: Unable to answer query for {image_path}. Run 'describe {image_path}' first or use a URL.")
                    else:
                        response_parts.append(f"\nAnswer for {image_path}")
                        response_parts.append(query_output)
                        logfire.info(f"Question answered for {image_path}")
                except Exception as e:
                    logfire.error("Image query error for {image_path}", image_path=image_path, exc_info=e)
                    response_parts.append(f"Error: Failed to answer query for {image_path}: {str(e)}. Ensure the file is valid or try using a URL.")

        if wants_mindmap:
            if not check_graphviz():
                response_parts.append("Error: Graphviz 'dot' not found. Install Graphviz and add to PATH.")
                return "\n".join(response_parts)
            
            print(f"\nGenerating Mindmap for {image_path}")
            unique_id = str(uuid.uuid4())
            current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            mindmap_image_file = os.path.abspath(f"mindmap_{current_time_str}_{unique_id[:8]}.png")
            
            if not description_output:
                response_parts.append("Error: No description available to generate mindmap. Please describe the image first.")
                return "\n".join(response_parts)

            try:
                mindmap_result = await mindmap_agent.generate_mindmap_workflow(image_path, mindmap_image_file, summary=description_output)
                if "Error" in mindmap_result:
                    logfire.error(f"Mindmap failed: {mindmap_result}")
                    response_parts.append(f"Mindmap error: {mindmap_result}")
                else:
                    response_parts.append(f"\nMindmap for {image_path}")
                    response_parts.append(mindmap_result)
                    logfire.info(f"Mindmap generated for {image_path}")
            except Exception as e:
                logfire.error("Mindmap generation error for {image_path}", image_path=image_path, exc_info=e)
                response_parts.append(f"Error: Failed to generate mindmap for {image_path}: {str(e)}")

        if is_podcast:
            elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
            if not elevenlabs_api_key:
                response_parts.append("Error: ELEVENLABS_API_KEY not set.")
                return "\n".join(response_parts)
            if not description_output:
                response_parts.append("Error: No description available. Run a description task first.")
                return "\n".join(response_parts)

            print(f"\nGenerating Podcast for {image_path}")
            unique_id = str(uuid.uuid4())
            script_file_initial_suggestion = f"script_{unique_id}.json"
            audio_file = f"podcast_{unique_id}.mp3"

            try:
                script_tool = create_script_generation_tool()
                print(f"Calling generate_script with summary_len={len(description_output) if description_output else 0}, output_file={script_file_initial_suggestion}")
                script_result = await script_tool.function(summary=description_output, output_file=script_file_initial_suggestion)
                
                if "Error" in script_result:
                    response_parts.append(f"Script error: {script_result}")
                    logfire.error(f"Script failed: {script_result}")
                else:
                    actual_script_json_path = script_result.split("Script saved to ")[1].strip()
                    response_parts.append(f"\nPodcast Script for {image_path}")
                    try:
                        with open(actual_script_json_path, 'r', encoding='utf-8') as f:
                            script_json_content = json.load(f)
                            for item in script_json_content:
                                response_parts.append(f"{item.get('speaker')}: {item.get('text')}")
                    except FileNotFoundError:
                        response_parts.append(f"Error: Script file not found at {actual_script_json_path}")
                    except json.JSONDecodeError:
                        response_parts.append(f"Error: Could not read JSON from script file at {actual_script_json_path}")
                    
                    logfire.info(f"Script saved to {actual_script_json_path}")
                    audio_tool = create_audio_generation_tool(elevenlabs_api_key)
                    audio_input = AudioInput(script_file=actual_script_json_path, output_file=audio_file)
                    audio_result = await audio_tool.function(audio_input)
                    if "Error" in audio_result:
                        response_parts.append(f"Audio error: {audio_result}")
                        logfire.error(f"Audio failed: {audio_result}")
                    else:
                        response_parts.append(f"\nPodcast Audio for {image_path}")
                        response_parts.append(audio_result)
                        logfire.info(f"Podcast generated at {audio_file}")
            except Exception as e:
                logfire.error("Podcast generation error for {image_path}", image_path=image_path, exc_info=e)
                response_parts.append(f"Error: Failed to generate podcast for {image_path}: {str(e)}")

    elif pdf_path:
        print(f"\nProcessing PDF: {pdf_path}")
        if not validate_pdf_file(pdf_path):
            response_parts.append(f"Error: Invalid PDF file: {pdf_path}")
            return "\n".join(response_parts)

        if not wants_summary and not wants_mindmap and not is_podcast and not is_question:
            response_parts.append(f"PDF content prepared for {pdf_path}. Choose an action: 'summarize', 'create mindmap', 'create podcast', or ask a question.")
            return "\n".join(response_parts)

        summary_output = None
        if wants_summary or is_podcast or wants_mindmap or is_question:
            print(f"\nGenerating Summary for PDF: {pdf_path}")
            summary_length = "150-250 words"
            try:
                summary_response = await pdf_agent.summarize_pdf(pdf_path, length=summary_length)
                summary_output = await _extract_response_content(summary_response)
                if "Error" in summary_output:
                    logfire.error(f"PDF summarization failed: {summary_output}")
                    response_parts.append(f"Summary error: {summary_output}")
                else:
                    if wants_summary:
                        response_parts.append(f"\nSummary for {pdf_path}")
                        response_parts.append(summary_output)
                    await _save_context(pdf_path, "pdf", summary_output, planner)
                    logfire.info(f"Summary generated for {pdf_path}")
            except Exception as e:
                logfire.error("PDF summarization error for {pdf_path}", pdf_path=pdf_path, exc_info=e)
                response_parts.append(f"Error: Failed to summarize PDF {pdf_path}: {str(e)}")

            if is_question and not wants_summary:
                print(f"\nAnswering question for {pdf_path}: {user_request}")
                try:
                    query_response = await pdf_agent.answer_question(pdf_path, user_request)
                    query_output = await _extract_response_content(query_response)
                    response_parts.append(f"\nAnswer for {pdf_path}")
                    response_parts.append(query_output)
                    logfire.info(f"Question answered for {pdf_path}")
                except Exception as e:
                    logfire.error("PDF query error for {pdf_path}", pdf_path=pdf_path, exc_info=e)
                    response_parts.append(f"Error: Failed to answer query for {pdf_path}: {str(e)}")

        if wants_mindmap:
            if not check_graphviz():
                response_parts.append("Error: Graphviz 'dot' not found. Install Graphviz and add to PATH.")
                return "\n".join(response_parts)
            
            print(f"\nGenerating Mindmap for {pdf_path}")
            unique_id = str(uuid.uuid4())
            current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            mindmap_image_file = os.path.abspath(f"mindmap_{current_time_str}_{unique_id[:8]}.png")
            
            if not summary_output:
                response_parts.append("Error: No summary available to generate mindmap. Please summarize the PDF first.")
                return "\n".join(response_parts)

            try:
                mindmap_result = await mindmap_agent.generate_mindmap_workflow(pdf_path, mindmap_image_file, summary=summary_output)
                if "Error" in mindmap_result:
                    logfire.error(f"Mindmap failed: {mindmap_result}")
                    response_parts.append(f"Mindmap error: {mindmap_result}")
                else:
                    response_parts.append(f"\nMindmap for {pdf_path}")
                    response_parts.append(mindmap_result)
                    logfire.info(f"Mindmap generated for {pdf_path}")
            except Exception as e:
                logfire.error("Mindmap generation error for {pdf_path}", pdf_path=pdf_path, exc_info=e)
                response_parts.append(f"Error: Failed to generate mindmap for {pdf_path}: {str(e)}")

        if is_podcast:
            elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
            if not elevenlabs_api_key:
                response_parts.append("Error: ELEVENLABS_API_KEY not set.")
                return "\n".join(response_parts)
            if not summary_output:
                response_parts.append("Error: No summary available. Run a summarization task first.")
                return "\n".join(response_parts)

            print(f"\nGenerating Podcast for {pdf_path}")
            unique_id = str(uuid.uuid4())
            script_file_initial_suggestion = f"script_{unique_id}.json"
            audio_file = f"podcast_{unique_id}.mp3"

            try:
                script_tool = create_script_generation_tool()
                print(f"Calling generate_script with summary_len={len(summary_output) if summary_output else 0}, output_file={script_file_initial_suggestion}")
                script_result = await script_tool.function(summary=summary_output, output_file=script_file_initial_suggestion)
                
                if "Error" in script_result:
                    response_parts.append(f"Script error: {script_result}")
                    logfire.error(f"Script failed: {script_result}")
                else:
                    actual_script_json_path = script_result.split("Script saved to ")[1].strip()
                    response_parts.append(f"\nPodcast Script for {pdf_path}")
                    try:
                        with open(actual_script_json_path, 'r', encoding='utf-8') as f:
                            script_json_content = json.load(f)
                            for item in script_json_content:
                                response_parts.append(f"{item.get('speaker')}: {item.get('text')}")
                    except FileNotFoundError:
                        response_parts.append(f"Error: Script file not found at {actual_script_json_path}")
                    except json.JSONDecodeError:
                        response_parts.append(f"Error: Could not read JSON from script file at {actual_script_json_path}")
                    
                    logfire.info(f"Script saved to {actual_script_json_path}")
                    audio_tool = create_audio_generation_tool(elevenlabs_api_key)
                    audio_input = AudioInput(script_file=actual_script_json_path, output_file=audio_file)
                    audio_result = await audio_tool.function(audio_input)
                    if "Error" in audio_result:
                        response_parts.append(f"Audio error: {audio_result}")
                        logfire.error(f"Audio failed: {audio_result}")
                    else:
                        response_parts.append(f"\nPodcast Audio for {pdf_path}")
                        response_parts.append(audio_result)
                        logfire.info(f"Podcast generated at {audio_file}")
            except Exception as e:
                logfire.error("Podcast generation error for {pdf_path}", pdf_path=pdf_path, exc_info=e)
                response_parts.append(f"Error: Failed to generate podcast for {pdf_path}: {str(e)}")

    elif url:
        print(f"\nProcessing URL: {url}")
        content_extracted, current_url_type = await _ensure_content(planner, url)
        if current_url_type is None:
            response_parts.append(content_extracted)
            return "\n".join(response_parts)

        if not wants_summary and not wants_mindmap and not is_podcast and not is_question:
            response_parts.append(f"Content prepared for {url}. Choose an action: 'summarize', 'create mindmap', 'create podcast', or ask a question.")
            return "\n".join(response_parts)

        summary_output = None
        if wants_summary or is_podcast or wants_mindmap or is_question:
            print(f"\nGenerating Summary for {url} ({current_url_type})")
            summary_length = "150-250 words"
            try:
                summary_response = None
                if current_url_type == "youtube":
                    summary_response = await youtube_agent.run(
                        f"Summarize content from {url} in {summary_length}, focusing on main points."
                    )
                elif current_url_type == "web":
                    summary_response = await web_agent.run(
                        f"Summarize content from {url} in {summary_length}, focusing on main points."
                    )
                
                summary_output = await _extract_response_content(summary_response)
                if "Error" in summary_output:
                    logfire.error(f"Summarization failed: {summary_output}")
                    response_parts.append(f"Summary error: {summary_output}")
                else:
                    if wants_summary:
                        response_parts.append(f"\nSummary for {url}")
                        response_parts.append(summary_output)
                    await _save_context(url, current_url_type, summary_output, planner)
                    logfire.info(f"Summary generated for {url}")
            except Exception as e:
                logfire.error("URL summarization error for {url}", url=url, exc_info=e)
                response_parts.append(f"Error: Failed to summarize {url}: {str(e)}")

            if is_question and not wants_summary:
                print(f"\nAnswering question for {url}: {user_request}")
                try:
                    query_response = None
                    if current_url_type == "youtube":
                        query_response = await youtube_agent.run(
                            f"Using transcript from {url}, answer: {user_request}"
                        )
                    elif current_url_type == "web":
                        query_response = await web_agent.run(
                            f"Using content from {url}, answer: {user_request}"
                        )
                    query_output = await _extract_response_content(query_response)
                    response_parts.append(f"\nAnswer for {url}")
                    response_parts.append(query_output)
                    logfire.info(f"Question answered for {url}")
                except Exception as e:
                    logfire.error("URL query error for {url}", url=url, exc_info=e)
                    response_parts.append(f"Error: Failed to answer query for {url}: {str(e)}")

        if wants_mindmap:
            if not check_graphviz():
                response_parts.append("Error: Graphviz 'dot' not found. Install Graphviz and add to PATH.")
                return "\n".join(response_parts)
            
            print(f"\nGenerating Mindmap for {url} ({current_url_type})")
            unique_id = str(uuid.uuid4())
            current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            mindmap_image_file = os.path.abspath(f"mindmap_{current_time_str}_{unique_id[:8]}.png")
            
            if not summary_output:
                response_parts.append("Error: No summary available to generate mindmap. Please summarize the content first.")
                return "\n".join(response_parts)

            try:
                mindmap_result = await mindmap_agent.generate_mindmap_workflow(url, mindmap_image_file, summary=summary_output)
                if "Error" in mindmap_result:
                    logfire.error(f"Mindmap failed: {mindmap_result}")
                    response_parts.append(f"Mindmap error: {mindmap_result}")
                else:
                    response_parts.append(f"\nMindmap for {url}")
                    response_parts.append(mindmap_result)
                    logfire.info(f"Mindmap generated for {url}")
            except Exception as e:
                logfire.error("Mindmap generation error for {url}", url=url, exc_info=e)
                response_parts.append(f"Error: Failed to generate mindmap for {url}: {str(e)}")

        if is_podcast:
            elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
            if not elevenlabs_api_key:
                response_parts.append("Error: ELEVENLABS_API_KEY not set.")
                return "\n".join(response_parts)
            if not summary_output:
                response_parts.append("Error: No summary available. Run a summarization task first.")
                return "\n".join(response_parts)

            print(f"\nGenerating Podcast for {url}")
            unique_id = str(uuid.uuid4())
            script_file_initial_suggestion = f"script_{unique_id}.json"
            audio_file = f"podcast_{unique_id}.mp3"

            try:
                script_tool = create_script_generation_tool()
                print(f"Calling generate_script with summary_len={len(summary_output) if summary_output else 0}, output_file={script_file_initial_suggestion}")
                script_result = await script_tool.function(summary=summary_output, output_file=script_file_initial_suggestion)
                
                if "Error" in script_result:
                    response_parts.append(f"Script error: {script_result}")
                    logfire.error(f"Script failed: {script_result}")
                else:
                    actual_script_json_path = script_result.split("Script saved to ")[1].strip()
                    response_parts.append(f"\nPodcast Script for {url}")
                    try:
                        with open(actual_script_json_path, 'r', encoding='utf-8') as f:
                            script_json_content = json.load(f)
                            for item in script_json_content:
                                response_parts.append(f"{item.get('speaker')}: {item.get('text')}")
                    except FileNotFoundError:
                        response_parts.append(f"Error: Script file not found at {actual_script_json_path}")
                    except json.JSONDecodeError:
                        response_parts.append(f"Error: Could not read JSON from script file at {actual_script_json_path}")
                    
                    logfire.info(f"Script saved to {actual_script_json_path}")
                    audio_tool = create_audio_generation_tool(elevenlabs_api_key)
                    audio_input = AudioInput(script_file=actual_script_json_path, output_file=audio_file)
                    audio_result = await audio_tool.function(audio_input)
                    if "Error" in audio_result:
                        response_parts.append(f"Audio error: {audio_result}")
                        logfire.error(f"Audio failed: {audio_result}")
                    else:
                        response_parts.append(f"\nPodcast Audio for {url}")
                        response_parts.append(audio_result)
                        logfire.info(f"Podcast generated at {audio_file}")
            except Exception as e:
                logfire.error("Podcast generation error for {url}", url=url, exc_info=e)
                response_parts.append(f"Error: Failed to generate podcast for {url}: {str(e)}")

    elif is_question:
        print(f"\nAnswering question from ChromaDB: {user_request}")
        try:
            query_output = await _query_chroma_db(user_request, planner)
            response_parts.append(query_output)
            logfire.info(f"Question answered from ChromaDB for query: {user_request}")
        except Exception as e:
            logfire.error("ChromaDB query error for {query}", query=user_request, exc_info=e)
            response_parts.append(f"Error: Failed to answer query from database: {str(e)}")

    elif is_podcast:
        elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
        if not elevenlabs_api_key:
            response_parts.append("Error: ELEVENLABS_API_KEY not set.")
            return "\n".join(response_parts)
        response_parts.append("Error: No content specified. Run a summarization/description task first or provide a URL/PDF/image.")
        return "\n".join(response_parts)

    else:
        response_parts.append("Provide a URL, PDF path, or image path/URL with a task (e.g., 'summarize https://example.com', 'summarize document.pdf', 'describe https://example.com/image.jpg', 'color of dog image.jpg') or ask a question about stored content (e.g., 'what is the main topic of the dog image').")

    return "\n".join(response_parts)

async def main():
    parser = argparse.ArgumentParser(description="Multi-Agent System for URL, PDF, and Image processing")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode.")
    parser.add_argument("--query", type=str, help="Run a single query.")
    args = parser.parse_args()

    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        logfire.error("GEMINI_API_KEY not set")
        print("Error: GEMINI_API_KEY not set in .env file.")
        return None

    # Initialize agents and planner
    global youtube_agent, web_agent, mindmap_agent, pdf_agent, image_agent, planner
    youtube_agent = YouTubeAgent(api_key=gemini_api_key)
    web_agent = WebAgent(api_key=gemini_api_key)
    mindmap_agent = MindmapAgent(api_key=gemini_api_key)
    pdf_agent = PDFAgent(api_key=gemini_api_key)
    image_agent = ImageAgent()
    planner = create_planner_agent(gemini_api_key)
    _load_context()

    if args.interactive:
        print("\n" + "="*60)
        print("  Welcome to the Multi-Agent Content Assistant!")
        print("="*60)
        print("I can summarize web pages, YouTube videos, PDFs, describe images, create mindmaps, generate podcasts, or answer questions about stored content.")
        print("\nType 'exit' to quit.")
        print("="*60 + "\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    print("\nAssistant: Exiting. Goodbye!")
                    logfire.info("Session ended.")
                    break
                if not user_input:
                    print("Assistant: Please enter a request.")
                    continue
                print("\nAssistant (processing...):")
                result = await run_task(planner, user_input)
                print(result)
            except KeyboardInterrupt:
                print("\nAssistant: Exiting. Goodbye!")
                logfire.info("Session ended via KeyboardInterrupt.")
                break
            except Exception as e:
                logfire.error("Session error", exc_info=e)
                print(f"Error: {str(e)}")
    elif args.query:
        print(f"\nProcessing query: {args.query}")
        try:
            result = await run_task(planner, args.query)
            print("\nResult")
            print(result)
        except Exception as e:
            logfire.error("Query error", exc_info=e)
            print(f"Error: {e}")
    else:
        print("Use --interactive for chatbot or --query '<request>' for single query.")

if __name__ == "__main__":
    asyncio.run(main())