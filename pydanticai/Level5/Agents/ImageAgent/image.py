import os
import argparse
import asyncio
import platform
import json
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, Tool
import logfire
from PIL import Image
import numpy as np

# Load environment variables
load_dotenv()

# Initialize Logfire
logfire_token = os.getenv('LOGFIRE_TOKEN')
if not logfire_token:
    print("Error: LOGFIRE_TOKEN not set in .env file.")
    exit(1)
logfire.configure(token=logfire_token)
logfire.info("Starting image analysis script")

# Fix Windows event loop
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Metadata file
METADATA_FILE = "image_metadata.json"

# Delete metadata file
if os.path.exists(METADATA_FILE):
    try:
        os.remove(METADATA_FILE)
        logfire.info(f"Deleted {METADATA_FILE} for fresh analysis")
    except Exception as e:
        logfire.error(f"Failed to delete {METADATA_FILE}: {str(e)}")

# Input models
class ImageAnalysisInput(BaseModel):
    image_path: str = Field(description="Local file path of the image to analyze.")

class QueryInput(BaseModel):
    image_path: str = Field(description="Image file path to query.")
    question: str = Field(description="Question about the image content.")

# Validate and inspect image
def validate_image_file(image_path: str) -> bool:
    supported_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
    if not os.path.isfile(image_path):
        logfire.error(f"Image file does not exist: {image_path}")
        return False
    ext = os.path.splitext(image_path)[1].lower()
    if ext not in supported_extensions:
        logfire.error(f"Unsupported image format: {image_path}. Supported: {supported_extensions}")
        return False
    try:
        with Image.open(image_path) as img:
            size = img.size
            mode = img.mode
            file_size = os.path.getsize(image_path) / 1024  # KB
            # Check contrast
            img_array = np.array(img.convert('L'))
            contrast = img_array.std()
            logfire.info(f"Image: Path={image_path}, Size={size}, Mode={mode}, FileSize={file_size:.2f}KB, Contrast={contrast:.2f}")
            if size[0] < 100 or size[1] < 100:
                logfire.error(f"Image too small: {size}. Minimum 100x100 pixels.")
                return False
            if file_size > 2048:
                logfire.error(f"Image too large: {file_size:.2f}KB. Maximum 2MB.")
                return False
            if contrast < 10:
                logfire.error(f"Image contrast too low: {contrast:.2f}. Image may be too dark or blurry.")
                return False
    except Exception as e:
        logfire.error(f"Failed to open image {image_path}: {str(e)}")
        return False
    return True

# Load metadata
def load_metadata(image_path: str) -> Optional[dict]:
    try:
        if not os.path.exists(METADATA_FILE):
            logfire.info(f"Metadata file not found: {METADATA_FILE}")
            return None
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        for entry in metadata:
            if entry['image_path'] == image_path:
                logfire.info(f"Found metadata for image: {image_path}")
                return entry
        return None
    except Exception as e:
        logfire.error(f"Failed to load metadata: {str(e)}")
        return None

# Save metadata
def save_metadata(image_path: str, description: str):
    try:
        metadata = []
        entry = {
            'image_path': image_path,
            'description': description,
            'timestamp': datetime.now().isoformat()
        }
        metadata.append(entry)
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        logfire.info(f"Saved metadata for {image_path} to {METADATA_FILE}")
    except Exception as e:
        logfire.error(f"Failed to save metadata: {str(e)}")

# Image Analysis Tool
def create_image_analysis_tool() -> Tool:
    def analyze_image(input_model: ImageAnalysisInput) -> str:
        image_path = input_model.image_path
        logfire.info(f"Analyzing image: {image_path}")
        if not validate_image_file(image_path):
            return f"Error: Invalid image file: {image_path}"
        return f"Image analysis requested for {image_path}"
    return Tool[ImageAnalysisInput](
        name="analyze_image",
        description="Analyzes an image and generates a fresh description.",
        function=analyze_image
    )

# Image Query Tool
def create_image_query_tool() -> Tool:
    def query_image(input_model: QueryInput) -> str:
        image_path = input_model.image_path
        question = input_model.question
        logfire.info(f"Answering question '{question}' for image: {image_path}")
        metadata = load_metadata(image_path)
        if not metadata:
            return f"Error: No description found for {image_path}. Analyze the image first."
        description = metadata['description']
        word_count = len(description.split())
        if word_count < 100:
            logfire.warn(f"Description too short: {word_count} words. Re-analyze recommended.")
            return f"Error: Description too short ({word_count} words). Please re-analyze the image."
        question_lower = question.lower()
        if 'color' in question_lower and 'color' not in description.lower():
            return f"Error: Description lacks color details for '{question}'. Re-analyze the image."
        if 'background' in question_lower and ('background' not in description.lower() and 'setting' not in description.lower()):
            return f"Error: Description lacks background details for '{question}'. Re-analyze the image."
        return description
    return Tool[QueryInput](
        name="query_image_content",
        description="Retrieves image description to answer questions.",
        function=query_image
    )

# Main execution
async def main():
    parser = argparse.ArgumentParser(description="Analyze any image and answer questions.")
    parser.add_argument("image_path", type=str, help="Local file path of the image (e.g., image.jpg).")
    args = parser.parse_args()

    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        logfire.error("GEMINI_API_KEY not set")
        print("Error: GEMINI_API_KEY not set in .env file.")
        exit(1)

    if not validate_image_file(args.image_path):
        print(f"Error: Invalid image file: {args.image_path}")
        exit(1)

    try:
        analysis_tool = create_image_analysis_tool()
        query_tool = create_image_query_tool()

        # Analysis Agent
        analysis_agent = Agent(
            model='google-gla:gemini-1.5-pro',
            api_key=gemini_api_key,
            tools=[analysis_tool],
            system_prompt=(
                'You are an expert image analyst capable of describing any image accurately. '
                'Analyze the image and provide a detailed description (100-150 words) covering: '
                '- Main subject(s) (e.g., animals like cats or dogs, objects like tables) with precise colors and features. '
                '- Background and setting (e.g., outdoor garden, indoor room, specific elements like bushes or walls). '
                '- Lighting conditions (e.g., daylight, artificial) and their effect on visibility. '
                '- Actions or states of subjects (e.g., resting, moving, static). '
                'Use only visible details, avoiding assumptions (e.g., don’t guess hidden features). '
                'If the image is unclear (e.g., low resolution, blurry), report the issue and describe limitations. '
                'Ensure the description is detailed, accurate, and supports questions about colors, background, or actions. '
                'Output exactly 100-150 words for consistency.'
            )
        )

        # Analyze image
        logfire.info(f"Attempting to analyze image: {args.image_path}")
        print(f"\nAttempting to analyze image: {args.image_path}\n")
        analysis_response = await analysis_agent.run(
            f"Analyze the image at {args.image_path}",
            files=[args.image_path]
        )
        analysis_output = analysis_response.output if hasattr(analysis_response, 'output') else str(analysis_response)
        word_count = len(analysis_output.split())
        if word_count < 100:
            logfire.warn(f"Analysis too short: {word_count} words")
            analysis_output += f"\nWarning: Description is short ({word_count} words). Additional details may be limited."
        logfire.info(f"Image analysis result: {analysis_output[:100]}...")
        print("\n--- Image Analysis ---")
        print(analysis_output)

        save_metadata(args.image_path, analysis_output)
        if "Error" in analysis_output:
            return

        # Query Agent
        query_agent = Agent(
            model='google-gla:gemini-1.5-pro',
            api_key=gemini_api_key,
            tools=[query_tool],
            system_prompt=(
                'You are an expert at answering image-related questions. '
                'Use the `query_image_content` tool to retrieve the description. '
                'Answer concisely (1-2 sentences) based only on the description, without speculation. '
                'If the description lacks relevant details, state so and suggest re-analysis.'
            )
        )

        # Interactive Q&A
        print("\n--- Interactive Q&A ---")
        print(f"Image analyzed: {args.image_path}. Ask questions or type 'exit' to quit.")
        while True:
            question = input("Question: ").strip()
            if question.lower() == 'exit':
                logfire.info("Exiting Q&A session")
                print("Exiting Q&A session.")
                break
            logfire.info(f"User asked: {question}")
            query_response = await query_agent.run(
                f"Using the description for {args.image_path}, answer: {question}"
            )
            query_output = query_response.output if hasattr(query_response, 'output') else str(query_response)
            logfire.info(f"Query response: {query_output}")
            print(f"Answer: {query_output}\n")

    except Exception as e:
        logfire.error(f"Unexpected error: {str(e)}")
        print(f"\nError: {e}")
        print("Troubleshooting:")
        print("1. Delete image_metadata.json: Remove-Item 'C:\\Users\\tript\\OneDrive\\Desktop\\py\\Level5\\image_metadata.json'")
        print("2. Verify image content (e.g., dog, table, cat) in an image viewer.")
        print("3. Ensure image is clear (>100x100 pixels, <2MB, good contrast).")
        print("4. Check GEMINI_API_KEY and LOGFIRE_TOKEN in .env.")
        print("5. Install dependencies: pip install pydantic-ai==0.2.17 python-dotenv logfire pillow numpy")
        print("6. Share terminal output and Logfire logs for help.")

if __name__ == "__main__":
    asyncio.run(main())
    