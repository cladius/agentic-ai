import logging
from typing import AsyncGenerator, override
from pydantic import BaseModel, Field
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.adk.agents.invocation_context import InvocationContext
from google.genai import types, Client as GenAIClient
from PIL import Image
from io import BytesIO
from pathlib import Path
from datetime import datetime
import re
import base64

logger = logging.getLogger(__name__)

# --- Constants from constants_and_models.py ---
MODEL_IMAGE_GENERATION = "gemini-2.0-flash-preview-image-generation"

# --- Image Generation Agent ---
class ImageGenerationAgent(BaseAgent):
    name: str = Field(default="ImageGenerationAgent")
    model: str = Field(default=MODEL_IMAGE_GENERATION)
    client: GenAIClient = Field(default_factory=lambda: GenAIClient())
    target_directory: Path = Field(default_factory=lambda: Path("image_generations"))

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, **data):
        super().__init__(**data)
        self.target_directory.mkdir(parents=True, exist_ok=True)

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        logger.info(f"[{self.name}] Starting image generation.")

        # Get input from session state or routing decision
        input_text = ctx.session.state.get("input_text", "")
        if not input_text:
            routing_decision = ctx.session.state.get("parsed_routing_decision", {})
            if isinstance(routing_decision, dict):
                input_text = routing_decision.get("instructions", "")

        if not input_text and hasattr(ctx, "content") and ctx.content and hasattr(ctx.content, "parts"):
            for part in ctx.content.parts:
                if hasattr(part, "text") and part.text:
                    input_text = part.text.strip()
                    break

        # Clean input to extract the image description
        input_text = re.sub(r'^(Generate|Create|Render)\s+(an\s+)?image\s+(of|for|about)\s*', '', input_text, flags=re.IGNORECASE).strip()

        if not input_text:
            error_response = "Error: No input provided for image generation."
            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=error_response)]
                ),
                author=self.name
            )
            return

        try:
            # Generate image using Gemini 2.0 Flash Preview Image Generation
            response = self.client.models.generate_content(
                model=self.model,
                contents=input_text,
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE']
                )
            )

            image_data = None
            text_response = ""
            for part in response.candidates[0].content.parts:
                if part.text is not None:
                    text_response += part.text + "\n"
                elif part.inline_data is not None:
                    image_data = part.inline_data.data

            if not image_data:
                raise ValueError("No image data returned by the model.")

            # Save the image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = self.target_directory / f"generated_image_{timestamp}.png"
            image = Image.open(BytesIO(image_data))
            image.save(image_path)

            # Store base64-encoded image and metadata in session state
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
            ctx.session.state["generated_image"] = {
                "path": str(image_path),
                "base64": base64_image,
                "description": input_text,
                "timestamp": timestamp
            }

            response_text = f"""
🖼️ Image Generated Successfully:
- Description: {input_text[:50]}{'...' if len(input_text) > 50 else ''}
- Saved to: {image_path}
- Text response: {text_response.strip()[:100]}{'...' if len(text_response.strip()) > 100 else ''}
- Image metadata stored in session state under 'generated_image'
            """.strip()

            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=response_text)]
                ),
                author=self.name
            )

        except Exception as e:
            logger.error(f"[{self.name}] Error generating image: {str(e)}")
            error_response = f"❌ Error generating image: {str(e)}"
            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=error_response)]
                ),
                author=self.name
            )