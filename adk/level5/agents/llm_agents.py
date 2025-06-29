import logging
import re
import base64
import os
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List, Optional
from typing_extensions import override
from google.adk.agents import LlmAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types, Client as GenAIClient
from pydantic import Field
from elevenlabs.client import ElevenLabs
from PIL import Image
from io import BytesIO
from level5.constants_and_models import (
    MODEL_GEMINI_FLASH, MODEL_GEMINI_2_FLASH, MODEL_GEMINI_LIVE, 
    MODEL_IMAGE_GENERATION, AUDIO_SAMPLE_RATE, AUDIO_BIT_DEPTH, AUDIO_CHANNELS, AudioConfig
)
from level5.utils import AudioProcessor
from level5.prompts import (
    ENHANCED_ROUTER_INSTRUCTION, TEXT_AGENT_INSTRUCTION, IMAGE_AGENT_INSTRUCTION,
    VIDEO_AGENT_INSTRUCTION, AUDIO_AGENT_INSTRUCTION, SCRIPT_GENERATOR_INSTRUCTION
)

logger = logging.getLogger(__name__)

# --- Helper Functions ---
def extract_text_from_message(message: Any) -> str:
    if not message:
        return ""
    if isinstance(message, types.Content):
        if message.parts and len(message.parts) > 0:
            first_part = message.parts[0]
            if hasattr(first_part, 'text'):
                return first_part.text
            elif isinstance(first_part, str):
                return first_part
    if isinstance(message, dict):
        if "parts" in message and isinstance(message["parts"], list) and len(message["parts"]) > 0:
            first_part = message["parts"][0]
            if isinstance(first_part, dict) and "text" in first_part:
                return first_part["text"]
            elif isinstance(first_part, str):
                return first_part
        if "text" in message:
            return message["text"]
        if "content" in message:
            return str(message["content"])
    if isinstance(message, str):
        return message
    return str(message)

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

# --- Script Generator Agent ---
class ScriptGeneratorAgent(LlmAgent):
    name: str = "ScriptGeneratorAgent"
    
    def __init__(self, name: str = "ScriptGeneratorAgent", model: str = MODEL_GEMINI_2_FLASH):
        super().__init__(
            name=name,
            model=model,
            instruction=SCRIPT_GENERATOR_INSTRUCTION,
            input_schema=None,
            output_key="podcast_script"
        )
    
    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        logger.info(f"[{self.name}] Starting podcast script generation.")
        input_text = ctx.session.state.get("input_text", "")

        if not input_text:
            input_text = ctx.session.state.get("processing_instructions", "")

        if not input_text:
            routing_decision = ctx.session.state.get("parsed_routing_decision", {})
            if isinstance(routing_decision, dict):
                input_text = routing_decision.get("instructions", "")

        if input_text:
            input_text = re.sub(r'^(Generate|Create)\s+a\s+podcast\s+script\s+(about|for|on)\s*', '', input_text, flags=re.IGNORECASE).strip()

        if not input_text:
            error_response = "Error: No input provided for script generation."
            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=error_response)]
                ),
                author=self.name
            )
            return

        try:
            ctx.session.state["input_text"] = input_text
            script_text = ""
            async for event in super()._run_async_impl(ctx):
                if event.content and event.content.parts:
                    script_text = extract_text_from_message(event.content)
                    break

            if not script_text:
                raise ValueError("No script generated by LLM.")

            ctx.session.state["podcast_script"] = script_text

            response_text = f"""
📝 Podcast Script Generated Successfully:
- Topic: {input_text[:50]}{'...' if len(input_text) > 50 else ''}
- Script stored in session state under 'podcast_script'
- Preview: {script_text[:100]}{'...' if len(script_text) > 100 else ''}
            """.strip()

            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=response_text)]
                ),
                author=self.name
            )
        except Exception as e:
            error_response = f"❌ Error generating podcast script: {str(e)}"
            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=error_response)]
                ),
                author=self.name
            )

# --- Podcast Generator Agent ---
class PodcastGeneratorAgent(BaseAgent):
    name: str
    model: Any
    client: Any = Field(default=None)
    voice_id_1: str = Field(default="EXAVITQu4vr4xnSDxMaL")  # Sarah (female)
    voice_id_2: str = Field(default="JBFqnCBsd6RMkjVDRZzb")  # George (male)
    model_id: str = Field(default="eleven_multilingual_v2")
    target_directory: Path = Field(default_factory=lambda: Path("audio_generations"))
    
    model_config = {"arbitrary_types_allowed": True}
    
    def __init__(self, name: str = "PodcastGenerator", model: Any = None):
        super().__init__(name=name, model=model or MODEL_GEMINI_2_FLASH)
        self.client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
        self.target_directory.mkdir(parents=True, exist_ok=True)
    
    def _split_script_into_speakers(self, script: str) -> List[Dict[str, str]]:
        segments = []
        current_speaker = 1
        
        paragraphs = script.split('\n\n')
        
        for paragraph in paragraphs:
            if paragraph.strip():
                segments.append({
                    "text": paragraph.strip(),
                    "speaker": current_speaker
                })
                current_speaker = 3 - current_speaker
        
        return segments
    
    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        logger.info(f"[{self.name}] Starting podcast generation.")
        
        script_text = ctx.session.state.get("podcast_script", "")
        
        if not script_text:
            script_text = ctx.session.state.get("input_text", "")
            
        if not script_text and hasattr(ctx, "content") and ctx.content and hasattr(ctx.content, "parts"):
            for part in ctx.content.parts:
                if hasattr(part, "text") and part.text:
                    script_text = part.text.strip()
                    break
                    
        script_text = re.sub(r'^Generate a podcast from this summary:\s*', '', script_text, flags=re.IGNORECASE).strip()
        
        if not script_text:
            error_response = "Error: No script or text provided for podcast generation."
            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=error_response)]
                ),
                author=self.name
            )
            return
        
        if len(script_text) > 2000:
            error_response = "Error: Input text exceeds 2000 character limit for ElevenLabs API."
            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=error_response)]
                ),
                author=self.name
            )
            return
        
        try:
            segments = self._split_script_into_speakers(script_text)
            
            audio_segments = []
            for segment in segments:
                voice_id = self.voice_id_1 if segment["speaker"] == 1 else self.voice_id_2
                audio = self.client.text_to_speech.convert(
                    text=segment["text"],
                    voice_id=voice_id,
                    model_id=self.model_id,
                    output_format="mp3_44100_128"
                )
                audio_segments.append(audio)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_path = self.target_directory / f"output_{timestamp}.mp3"
            
            with open(audio_path, "wb") as f:
                for audio in audio_segments:
                    for chunk in audio:
                        if chunk:
                            f.write(chunk)
            
            response_text = f"""
🎙️ Podcast Audio Generated Successfully:
- Output saved to: {audio_path}
- Using voices: Sarah (female) and George (male)
- Input text: {script_text[:50]}{'...' if len(script_text) > 50 else ''}
            """.strip()
            
            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=response_text)]
                ),
                author=self.name
            )
        except Exception as e:
            error_response = f"❌ Error generating podcast audio: {str(e)}"
            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=error_response)]
                ),
                author=self.name
            )

# --- Real-time Audio Agent ---
class RealtimeAudioAgent(BaseAgent):
    name: str
    model: str
    audio_processor: Optional[AudioProcessor] = None
    
    model_config = {"arbitrary_types_allowed": True}
    
    def __init__(self, name: str = "RealtimeAudioAgent", model: str = MODEL_GEMINI_LIVE):
        super().__init__(name=name, model=model)
        self.audio_processor = AudioProcessor()
    
    async def process_audio_stream(self, audio_data: bytes, config: AudioConfig) -> Dict[str, Any]:
        try:
            base64_audio = self.audio_processor.audio_to_base64(audio_data)
            audio_input = {
                "audio": {
                    "data": base64_audio,
                    "mimeType": f"audio/pcm;rate={config.sample_rate}"
                }
            }
            result = {
                "transcription": "Audio processed successfully",
                "analysis": "Real-time audio analysis would be performed here",
                "metadata": {
                    "sample_rate": config.sample_rate,
                    "duration": len(audio_data) / (config.sample_rate * 2),
                    "format": config.format
                }
            }
            return result
        except Exception as e:
            logger.error(f"Error processing audio stream: {e}")
            return {
                "error": str(e),
                "transcription": "",
                "analysis": "Failed to process audio"
            }
    
    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        logger.info(f"[{self.name}] Starting real-time audio processing.")
        
        audio_config_data = ctx.session.state.get("audio_config", {})
        audio_config = AudioConfig(**audio_config_data)
        instructions = ctx.session.state.get("processing_instructions", "Process this audio input")
        audio_file_path = ctx.session.state.get("audio_file_path")
        
        if audio_file_path and os.path.exists(audio_file_path):
            try:
                audio_data = self.audio_processor.convert_to_pcm_16khz(audio_file_path)
                result = await self.process_audio_stream(audio_data, audio_config)
                
                response_text = f"""
🎵 Real-time Audio Processing Results:
📝 Transcription: {result.get('transcription', 'N/A')}
🔍 Analysis: {result.get('analysis', 'N/A')}
📊 Metadata:
- Sample Rate: {result.get('metadata', {}).get('sample_rate', 'N/A')} Hz
- Duration: {result.get('metadata', {}).get('duration', 'N/A'):.2f} seconds
- Format: {result.get('metadata', {}).get('format', 'N/A')}
Instructions followed: {instructions}
                """.strip()
                
                ctx.session.state["realtime_audio_result"] = result
                yield Event(
                    content=types.Content(
                        role='assistant',
                        parts=[types.Part(text=response_text)]
                    ),
                    author=self.name
                )
            except Exception as e:
                error_response = f"❌ Error processing audio file: {str(e)}"
                yield Event(
                    content=types.Content(
                        role='assistant',
                        parts=[types.Part(text=error_response)]
                    ),
                    author=self.name
                )
        else:
            response_text = """
🎵 Real-time Audio Agent Ready
To process audio, please provide:
1. Audio file path in session state under 'audio_file_path'
2. Audio configuration (optional)
Supported formats: WAV, MP3 (will be converted to 16kHz PCM)
Real-time streaming capabilities available for live audio processing.
            """.strip()
            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=response_text)]
                ),
                author=self.name
            )

# --- Define Individual LLM Agents ---
enhanced_router_agent = LlmAgent(
    name="RouterAgent",
    model=MODEL_GEMINI_FLASH,
    instruction=ENHANCED_ROUTER_INSTRUCTION,
    input_schema=None,
    output_key="routing_decision"
)

text_agent = LlmAgent(
    name="TextAnalysisAgent",
    model=MODEL_GEMINI_2_FLASH,
    instruction=TEXT_AGENT_INSTRUCTION,
    input_schema=None,
    output_key="text_analysis_result"
)

image_agent = LlmAgent(
    name="ImageAnalysisAgent",
    model=MODEL_GEMINI_2_FLASH,
    instruction=IMAGE_AGENT_INSTRUCTION,
    input_schema=None,
    output_key="image_analysis_result"
)

video_agent = LlmAgent(
    name="VideoAnalysisAgent",
    model=MODEL_GEMINI_2_FLASH,
    instruction=VIDEO_AGENT_INSTRUCTION,
    input_schema=None,
    output_key="video_analysis_result"
)

audio_agent = LlmAgent(
    name="AudioAnalysisAgent",
    model=MODEL_GEMINI_2_FLASH,
    instruction=AUDIO_AGENT_INSTRUCTION,
    input_schema=None,
    output_key="audio_analysis_result"
)

# --- Create Agent Instances ---
realtime_audio_agent = RealtimeAudioAgent()
podcast_agent = PodcastGeneratorAgent()
script_generator_agent = ScriptGeneratorAgent()
image_generation_agent = ImageGenerationAgent()