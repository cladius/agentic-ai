import os
import json
import logfire
from pydantic import BaseModel, Field
from pydantic_ai import Agent, Tool
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider
from PIL import Image
import requests
from io import BytesIO
import hashlib
import base64
import asyncio
from dotenv import load_dotenv
from typing import Optional
try:
    import google.generativeai as genai
except ImportError:
    genai = None
    print("Warning: google-generativeai not installed. Install with `pip install google-generativeai` for image analysis.")

load_dotenv()

logfire_token = os.getenv('LOGFIRE_TOKEN')
if not logfire_token:
    print("Error: LOGFIRE_TOKEN not set in .env file.")
    logfire.error("LOGFIRE_TOKEN not set in image.py")
    logfire_token = "dummy_token_if_not_set"
logfire.configure(token=logfire_token)
logfire.info("Starting image.py module for image analysis")

METADATA_FILE = "image_metadata.json"

def initialize_metadata():
    """Initializes an empty metadata JSON file if it doesn't exist."""
    if not os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            logfire.info(f"Created {METADATA_FILE}")
        except Exception as e:
            logfire.error(f"Failed to create {METADATA_FILE}: {str(e)}")
    else:
        logfire.info(f"{METADATA_FILE} already exists")

initialize_metadata()

def validate_image_file(image_path: str) -> bool:
    """
    Validates if an image file or URL is accessible and valid.
    Checks file existence, format, and permissions.
    """
    if image_path.startswith('http'):
        try:
            response = requests.head(image_path, timeout=5)
            if response.status_code != 200:
                logfire.error(f"Invalid image URL {image_path}: Status code {response.status_code}")
                return False
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                logfire.error(f"Invalid image URL {image_path}: Content type {content_type}")
                return False
            logfire.info(f"Valid image URL: {image_path}")
            return True
        except requests.RequestException as e:
            logfire.error(f"Invalid image URL {image_path}: {str(e)}")
            return False
    else:
        norm_path = os.path.normpath(image_path)
        logfire.info(f"Validating local image: {norm_path}")
        base_dir = os.path.dirname(norm_path)
        filename = os.path.basename(norm_path)
        if not os.path.exists(base_dir):
            logfire.error(f"Directory does not exist: {base_dir}")
            return False
        try:
            files_in_dir = os.listdir(base_dir)
            matching_files = [f for f in files_in_dir if f.lower() == filename.lower()]
            if not matching_files:
                logfire.error(f"Image file does not exist: {norm_path}")
                return False
            actual_path = os.path.join(base_dir, matching_files[0])
            logfire.info(f"Found matching file: {actual_path}")
            with open(actual_path, 'rb') as f:
                img_data = f.read()
            img = Image.open(BytesIO(img_data))
            img.verify()
            img = Image.open(BytesIO(img_data))
            logfire.info(f"Valid image: Path={actual_path}, Size={img.size}, Mode={img.mode}, FileSize={len(img_data)/1024:.2f}KB")
            return True
        except PermissionError as e:
            logfire.error(f"Permission denied for {norm_path}: {str(e)}")
            return False
        except Exception as e:
            logfire.error(f"Invalid image file {norm_path}: {str(e)}")
            return False

def get_image_data(image_path: str) -> bytes:
    """
    Reads image data as bytes from a local file or URL.
    Validates accessibility and returns raw image data.
    """
    if image_path.startswith('http'):
        try:
            response = requests.get(image_path, timeout=10)
            response.raise_for_status()
            logfire.info(f"Downloaded image from {image_path}")
            return response.content
        except requests.RequestException as e:
            logfire.error(f"Failed to download image {image_path}: {str(e)}")
            raise ValueError(f"Cannot access image URL: {image_path}")
    else:
        norm_path = os.path.normpath(image_path)
        base_dir = os.path.dirname(norm_path)
        filename = os.path.basename(norm_path)
        try:
            files_in_dir = os.listdir(base_dir)
            matching_files = [f for f in files_in_dir if f.lower() == filename.lower()]
            if not matching_files:
                logfire.error(f"Image file does not exist: {norm_path}")
                raise ValueError(f"Image file does not exist: {norm_path}")
            actual_path = os.path.join(base_dir, matching_files[0])
            logfire.info(f"Reading image data from {actual_path}")
            with open(actual_path, 'rb') as f:
                data = f.read()
                logfire.info(f"Read image data from {actual_path}, Size={len(data)/1024:.2f}KB")
                return data
        except PermissionError as e:
            logfire.error(f"Permission denied for {norm_path}: {str(e)}")
            raise ValueError(f"Permission denied for {norm_path}: {str(e)}")
        except Exception as e:
            logfire.error(f"Failed to read image {norm_path}: {str(e)}")
            raise ValueError(f"Cannot read image file: {norm_path}")

def check_image_description_in_db(image_path: str) -> Optional[dict]:
    """
    Checks image_metadata.json for an existing image description.
    Returns description and metadata if found, else None.
    """
    try:
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        if not isinstance(metadata, dict):
            logfire.error(f"{METADATA_FILE} contains invalid data (not a dictionary). Resetting to empty dictionary.")
            metadata = {}
            with open(METADATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
        image_data = get_image_data(image_path)
        image_hash = hashlib.md5(image_data).hexdigest()
        if image_hash in metadata and metadata[image_hash]['path'].lower() == image_path.lower():
            logfire.info(f"Found image description for {image_path}")
            return {'content': metadata[image_hash]['description'], 'metadata': {'path': image_path}}
        logfire.info(f"No image description found for {image_path}")
        return None
    except Exception as e:
        logfire.error(f"Failed to check image description for {image_path}: {str(e)}")
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

class ImageAnalysisInput(BaseModel):
    """Pydantic model for image analysis input."""
    image_path: str = Field(description="Path or URL to the image file.")

class ImageQueryInput(BaseModel):
    """Pydantic model for querying image content."""
    image_path: str = Field(description="Path or URL to the image file.")
    question: str = Field(description="Question about the image content.")

def create_image_analysis_tool() -> Tool:
    """Creates a tool to analyze images and generate descriptions."""
    async def analyze_image(input_model: ImageAnalysisInput) -> str:
        """
        Analyzes an image and generates a 100-150 word description.
        Stores the description in image_metadata.json and returns it.
        """
        image_path = input_model.image_path
        logfire.info(f"Analyzing image: {image_path}")
        
        if not validate_image_file(image_path):
            return f"Error: Invalid image: {image_path}. Ensure the file exists, is a valid image (JPEG/PNG), and you have read permissions."

        try:
            image_data = get_image_data(image_path)
            image_hash = hashlib.md5(image_data).hexdigest()
            
            existing_data = check_image_description_in_db(image_path)
            if existing_data:
                logfire.info(f"Returning cached description for {image_path}")
                return existing_data['content']

            if not genai:
                return f"Error: google-generativeai library required for image analysis. Install with `pip install google-generativeai`."
            
            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            async def analyze():
                img = Image.open(BytesIO(image_data))
                img_format = img.format.lower() if img.format else 'jpeg'
                mime_type = f'image/{img_format}'
                encoded_image = base64.b64encode(image_data).decode('utf-8')
                prompt = (
                    "Analyze the image and provide a detailed description (100-150 words) covering: "
                    "- Main subject(s) (e.g., animals like cats or dogs, objects like tables) with precise colors and features. "
                    "- Background and setting (e.g., outdoor garden, indoor room, specific elements like bushes or walls). "
                    "- Lighting conditions (e.g., daylight, artificial) and their effect on visibility. "
                    "- Actions or states of subjects (e.g., resting, moving, static). "
                    "Use only visible details, avoiding assumptions (e.g., don’t guess hidden features). "
                    "If the image is unclear (e.g., low resolution, blurry), report the issue and describe limitations. "
                    "Ensure the description is detailed, accurate, and supports questions about colors, background, or actions."
                )
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: model.generate_content([prompt, {'mime_type': mime_type, 'data': encoded_image}])
                )
                description = response.text
                word_count = len(description.split())
                if word_count < 100 or word_count > 150:
                    raise ValueError(f"Description length {word_count} words is outside 100-150 word range.")
                return description
            
            description = await try_with_retry(analyze)
            
            try:
                with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except FileNotFoundError:
                metadata = {}
                logfire.warning(f"{METADATA_FILE} not found, creating new")
            
            metadata[image_hash] = {'path': image_path, 'description': description}
            try:
                with open(METADATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
                logfire.info(f"Saved description to {METADATA_FILE} for {image_path}")
            except Exception as e:
                logfire.error(f"Failed to save metadata for {image_path}: {str(e)}")
            
            return description
        except Exception as e:
            logfire.error(f"Image analysis failed for {image_path}: {str(e)}")
            return f"Error: Failed to analyze image {image_path}: {str(e)}"

    return Tool[ImageAnalysisInput](
        name="analyze_image",
        description="Analyzes an image and returns a description (100-150 words). Stores description in image_metadata.json.",
        function=analyze_image
    )

def create_image_query_tool() -> Tool:
    """Creates a tool to answer questions about images using stored descriptions."""
    async def query_image_content(input_model: ImageQueryInput) -> str:
        """
        Answers a question about an image using its stored description from image_metadata.json.
        Uses Gemini model to generate precise answers based on the description.
        """
        image_path = input_model.image_path
        question = input_model.question
        logfire.info(f"Answering question for image: {image_path}, Question: {question}")

        if not validate_image_file(image_path):
            return f"Error: Invalid image: {image_path}. Ensure the file exists, is a valid image (JPEG/PNG), and you have read permissions."

        try:
            existing_data = check_image_description_in_db(image_path)
            if not existing_data:
                logfire.warning(f"No description found for {image_path}. Run 'analyze_image' first.")
                return f"Error: No description found for {image_path}. Please run 'analyze_image' first."

            description = existing_data['content']
            if not genai:
                return f"Error: google-generativeai library required for image query. Install with `pip install google-generativeai`."

            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
            model = genai.GenerativeModel('gemini-1.5-flash')

            async def query():
                prompt = (
                    f"Based on the following image description, answer the question: {question}\n\n"
                    f"Description:\n{description}\n\n"
                    "Provide a concise and accurate answer (50-100 words) based only on the description. "
                    "If the description lacks details to answer the question, state that clearly."
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
            logfire.info(f"Answered question for {image_path}: {answer[:50]}...")
            return answer
        except Exception as e:
            logfire.error(f"Image query failed for {image_path}: {str(e)}")
            return f"Error: Failed to answer question for {image_path}: {str(e)}"

    return Tool[ImageQueryInput](
        name="query_image_content",
        description="Answers a question about an image using its stored description from image_metadata.json.",
        function=query_image_content
    )

class ImageAgent(Agent):
    """
    Specialized agent for analyzing images and answering questions about them.
    Uses Gemini model and stores descriptions in image_metadata.json.
    """
    def __init__(self):
        super().__init__(
            model=GeminiModel('gemini-1.5-flash-latest', provider=GoogleGLAProvider(api_key=os.getenv('GEMINI_API_KEY'))),
            api_key=os.getenv('GEMINI_API_KEY'),
            tools=[
                create_image_analysis_tool(),
                create_image_query_tool()
            ],
            system_prompt=(
                'You are an expert image analysis assistant capable of describing images and answering questions about them. '
                '1. **Image Analysis**: Use the `analyze_image` tool to generate a 100-150 word description of an image (local path or URL), covering subjects, colors, background, lighting, and actions. '
                '2. **Question Answering**: Use the `query_image_content` tool to answer questions about an image based on its stored description. '
                '3. **Error Handling**: Provide clear error messages for invalid images, missing descriptions, or API issues. '
                'Store descriptions in image_metadata.json and use only verified data without assumptions.'
            )
        )