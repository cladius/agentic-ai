import logging
import os
import json
import re
import base64
import asyncio
import aiofiles
from typing import AsyncGenerator, Dict, Any, List, Optional
from enum import Enum
from dotenv import load_dotenv
from typing import Optional
from typing_extensions import override
from google.adk.agents import LlmAgent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.genai import types, Client as GenAIClient
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.events import Event
from pydantic import BaseModel, Field
from elevenlabs.client import ElevenLabs
from pathlib import Path
from datetime import datetime
from pydub import AudioSegment
import sys
from PIL import Image
from io import BytesIO
import chromadb
import hashlib
import requests
from bs4 import BeautifulSoup

# --- Constants and Configuration ---
APP_NAME = "multimodal_agent_app"
USER_ID = "default_user"
SESSION_ID = f"session_{USER_ID}"
MODEL_GEMINI_FLASH = "gemini-1.5-flash"
MODEL_GEMINI_2_FLASH = "gemini-2.0-flash-exp"
MODEL_GEMINI_LIVE = "gemini-2.0-flash-live-001"
MODEL_IMAGE_GENERATION = "gemini-2.0-flash-preview-image-generation"
AUDIO_SAMPLE_RATE = 16000
AUDIO_BIT_DEPTH = 16
AUDIO_CHANNELS = 1

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Load Environment Variables ---
load_dotenv()
if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("GOOGLE_API_KEY environment variable not set.")
if not os.getenv("ELEVENLABS_API_KEY"):
    raise ValueError("ELEVENLABS_API_KEY environment variable not set.")

# --- Enums and Models ---
class ContentType(Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    REALTIME_AUDIO = "realtime_audio"
    SPEECH_GENERATION = "speech_generation"
    IMAGE_GENERATION = "image_generation"
    SCRIPT_GENERATION = "script_generation"

class RoutingDecision(BaseModel):
    content_types: List[str] = Field(default_factory=list)
    processing_plan: str = ""
    requires_multimodal: bool = False
    primary_agent: str = "text"
    instructions: str = ""
    audio_config: Optional[Dict[str, Any]] = None

class AgentResponse(BaseModel):
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    agent_name: str = ""
    error_message: Optional[str] = None

class AudioConfig(BaseModel):
    sample_rate: int = AUDIO_SAMPLE_RATE
    bit_depth: int = AUDIO_BIT_DEPTH
    channels: int = AUDIO_CHANNELS
    format: str = "pcm"
    realtime: bool = False

# --- Audio Processing Utilities ---
class AudioProcessor:
    @staticmethod
    def convert_to_pcm_16khz(audio_file_path: str) -> bytes:
        try:
            audio = AudioSegment.from_file(audio_file_path)
            audio = audio.set_channels(1)
            audio = audio.set_frame_rate(AUDIO_SAMPLE_RATE)
            audio = audio.set_sample_width(2)
            output_path = "temp_pcm.wav"
            audio.export(output_path, format="wav")
            with open(output_path, "rb") as f:
                pcm_data = f.read()
            os.remove(output_path)
            return pcm_data
        except Exception as e:
            logger.error(f"Error processing audio file: {e}")
            raise
    
    @staticmethod
    def audio_to_base64(audio_data: bytes) -> str:
        return base64.b64encode(audio_data).decode('utf-8')
    
    @staticmethod
    async def process_audio_file_async(file_path: str) -> str:
        loop = asyncio.get_event_loop()
        audio_data = await loop.run_in_executor(None, AudioProcessor.convert_to_pcm_16khz, file_path)
        return AudioProcessor.audio_to_base64(audio_data)

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
            instruction="""
You are a podcast script generator. Your task is to create engaging, conversational podcast scripts based on the provided topic or summary.

- Generate a script of 300-500 words suitable for a 3-5 minute podcast segment.
- Use a friendly, conversational tone as if speaking to a general audience.
- Include an introduction, main content, and a closing statement.
- Structure the script with clear sections (e.g., Intro, Main Points, Outro).
- If the input is a topic, create a script from scratch.
- If the input is a summary, expand it into a full script.
- **IMPORTANT: The entire script MUST be less than 2000 characters (including spaces) to fit the ElevenLabs API limit.**
- Store the generated script in session state under 'podcast_script'.

Example Input: "The impact of AI on healthcare"
Example Output:
# Podcast Script: The Impact of AI on Healthcare

**Intro**  
Hey everyone, welcome back to the Tech Talk Podcast! I'm your host, Alex, and today we're diving into something super exciting: how artificial intelligence is transforming healthcare. AI is changing the game, and I can't wait to share how it's making a difference in our lives. So, let's get started!

**Main Points**  
First off, AI is revolutionizing diagnostics. Machine learning models can analyze medical images like X-rays or MRIs with incredible accuracy, often spotting issues faster than human doctors. For example, AI systems are helping detect early signs of cancer, which can be a lifesaver.  

Next, AI is personalizing patient care. By analyzing data from wearables and health records, AI can recommend tailored treatment plans. Imagine a virtual health coach that knows exactly what you need to stay healthy!  

Finally, AI is streamlining hospital operations. From scheduling appointments to predicting patient admissions, AI helps hospitals run smoother, so doctors can focus on what matters most—caring for patients.

**Outro**  
That's it for today's episode, folks! AI in healthcare is just the beginning, and I'm so excited to see where this tech takes us. If you enjoyed this, subscribe for more tech insights, and let us know what topics you want to hear next. Until then, stay curious and take care!

---

Return the script as plain text and store it in session state under 'podcast_script'.
            """,
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

# --- ChromaDB Integration ---
class ChromaDBManager:
    def __init__(self, podcast_agent=None, text_agent=None, image_generation_agent=None):
        self.client = chromadb.Client()
        try:
            self.collection = self.client.get_collection(name="link_data")
        except chromadb.errors.NotFoundError:
            self.collection = self.client.create_collection(name="link_data")
        self.podcast_agent = podcast_agent
        self.text_agent = text_agent
        self.image_generation_agent = image_generation_agent

    def store_document(self, url: str, content: str, content_type: str = "text") -> str:
        doc_id = hashlib.md5(url.encode()).hexdigest()
        try:
            # Check if document already exists
            existing = self.collection.get(ids=[doc_id])
            if existing and existing["ids"]:
                # Update existing document
                self.collection.update(
                    documents=[content],
                    metadatas=[{"url": url, "content_type": content_type}],
                    ids=[doc_id]
                )
            else:
                # Add new document
                self.collection.add(
                    documents=[content],
                    metadatas=[{"url": url, "content_type": content_type}],
                    ids=[doc_id]
                )
        except Exception as e:
            logger.error(f"Error storing document: {str(e)}")
            # Try to add as new document if update fails
            self.collection.add(
                documents=[content],
                metadatas=[{"url": url, "content_type": content_type}],
                ids=[doc_id]
            )
        return doc_id

    def search_similar(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return [
            {
                "id": id,
                "content": doc,
                "url": meta["url"],
                "content_type": meta["content_type"]
            }
            for id, doc, meta in zip(results["ids"][0], results["documents"][0], results["metadatas"][0])
        ]

    def get_all_documents(self) -> List[Dict[str, Any]]:
        results = self.collection.get()
        return [
            {
                "id": id,
                "content": doc,
                "url": meta["url"],
                "content_type": meta["content_type"]
            }
            for id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"])
        ]

    async def generate_summary(self, doc_ids: List[str]) -> str:
        try:
            docs = self.collection.get(ids=doc_ids)
            if not docs or not docs["documents"]:
                return "Error: No documents found for the provided IDs"
            
            combined_content = "\n\n".join(docs["documents"])
            if not combined_content:
                return "Error: No content available to summarize"

            # Create a session for the summary generation
            session = await session_service.create_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=f"summary_{doc_ids[0]}",
                state={"input_text": f"Summarize this content: {combined_content}"}
            )

            # Prepare content for the agent
            content = types.Content(role='user', parts=[types.Part(text=session.state["input_text"])])

            # Create proper InvocationContext
            invocation_context = InvocationContext(
                session=session,
                session_service=session_service,
                invocation_id=f"summary_{doc_ids[0]}",
                agent=self.text_agent,
                content=content
            )

            # Run the text agent
            events = self.text_agent.run_async(invocation_context)

            final_response = "No summary generated."
            async for event in events:
                if event.is_final_response() and event.content and event.content.parts:
                    final_response = event.content.parts[0].text
                    break

            return final_response
        except Exception as e:
            return f"Error generating summary: {str(e)}"

    async def generate_podcast(self, doc_ids: List[str]) -> str:
        try:
            # Retrieve documents from ChromaDB
            docs = self.collection.get(ids=doc_ids)
            if not docs or not docs["documents"]:
                return "Error: No documents found for the provided IDs"
            
            combined_content = "\n\n".join(docs["documents"])
            if not combined_content:
                return "Error: No content available to generate podcast"

            # Get or create session
            session = await session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID
            )
            if not session:
                session = await session_service.create_session(
                    app_name=APP_NAME,
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    state={"conversation_history": [], "input_text": "", "podcast_script": "", "generated_image": {}}
                )
            
            # Update session state with input
            session.state["input_text"] = combined_content
            session.state["processing_instructions"] = "Convert the provided text into engaging spoken audio using ElevenLabs TTS"
            
            # Prepare content for the agent
            content = types.Content(role='user', parts=[types.Part(text=f"Generate a podcast from this text: {combined_content}")])
            
            # Create proper InvocationContext
            invocation_context = InvocationContext(
                session=session,
                session_service=session_service,
                invocation_id=f"podcast_{doc_ids[0]}",
                agent=self.podcast_agent,
                content=content
            )
            
            # Run the podcast agent
            events = self.podcast_agent.run_async(invocation_context)
            
            # Collect response
            final_response = "No response captured."
            async for event in events:
                if event.is_final_response() and event.content and event.content.parts:
                    final_response = event.content.parts[0].text
                    break
            
            return final_response
        
        except Exception as e:
            logger.error(f"Error generating podcast: {str(e)}")
            return f"❌ Error generating podcast: {str(e)}"

    async def generate_image(self, doc_ids: List[str]) -> str:
        try:
            docs = self.collection.get(ids=doc_ids)
            if not docs or not docs["documents"]:
                return "Error: No documents found for the provided IDs"
            
            combined_content = "\n\n".join(docs["documents"])
            if not combined_content:
                return "Error: No content available to generate image"

            # Create a session for image generation
            session = await session_service.create_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=f"image_{doc_ids[0]}",
                state={"input_text": f"Generate an image based on this content: {combined_content}"}
            )

            # Prepare content for the agent
            content = types.Content(role='user', parts=[types.Part(text=session.state["input_text"])])

            # Create proper InvocationContext
            invocation_context = InvocationContext(
                session=session,
                session_service=session_service,
                invocation_id=f"image_{doc_ids[0]}",
                agent=self.image_generation_agent,
                content=content
            )

            # Run the image generation agent
            events = self.image_generation_agent.run_async(invocation_context)

            final_response = "No image generated."
            async for event in events:
                if event.is_final_response() and event.content and event.content.parts:
                    final_response = event.content.parts[0].text
                    break

            return final_response
        except Exception as e:
            return f"Error generating image: {str(e)}"

class LinkProcessor:
    def __init__(self, chroma_manager: ChromaDBManager):
        self.chroma_manager = chroma_manager

    def process_link(self, url: str) -> Optional[str]:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            content_type = response.headers.get('content-type', '').lower()
            
            if 'text/html' in content_type:
                soup = BeautifulSoup(response.text, 'html.parser')
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text(separator='\n', strip=True)
                return self.chroma_manager.store_document(url, text, "text")
            
            elif 'image/' in content_type:
                return self.chroma_manager.store_document(url, url, "image")
            
            elif 'application/pdf' in content_type:
                return self.chroma_manager.store_document(url, url, "pdf")
            
            else:
                return self.chroma_manager.store_document(url, response.text, "other")
                
        except Exception as e:
            logger.error(f"Error processing link {url}: {str(e)}")
            return None

# --- Enhanced Multimodal Orchestrator Agent ---
class MultimodalOrchestratorAgent(BaseAgent):
    name: str
    text_agent: LlmAgent
    image_agent: LlmAgent
    video_agent: LlmAgent
    audio_agent: LlmAgent
    realtime_audio_agent: RealtimeAudioAgent
    podcast_agent: PodcastGeneratorAgent
    script_generator_agent: ScriptGeneratorAgent
    image_generation_agent: ImageGenerationAgent
    router_agent: LlmAgent
    chroma_manager: Optional[ChromaDBManager] = None
    link_processor: Optional[LinkProcessor] = None

    model_config = {"arbitrary_types_allowed": True}

    def __init__(
        self,
        name: str,
        text_agent: LlmAgent,
        image_agent: LlmAgent,
        video_agent: LlmAgent,
        audio_agent: LlmAgent,
        realtime_audio_agent: RealtimeAudioAgent,
        podcast_agent: PodcastGeneratorAgent,
        script_generator_agent: ScriptGeneratorAgent,
        image_generation_agent: ImageGenerationAgent,
        router_agent: LlmAgent
    ):
        chroma_manager = ChromaDBManager(
            podcast_agent=podcast_agent,
            text_agent=text_agent,
            image_generation_agent=image_generation_agent
        )
        link_processor = LinkProcessor(chroma_manager)
        
        sub_agents_list = [
            router_agent,
            text_agent,
            image_agent,
            video_agent,
            audio_agent,
            realtime_audio_agent,
            podcast_agent,
            script_generator_agent,
            image_generation_agent
        ]
        super().__init__(
            name=name,
            text_agent=text_agent,
            image_agent=image_agent,
            video_agent=video_agent,
            audio_agent=audio_agent,
            realtime_audio_agent=realtime_audio_agent,
            podcast_agent=podcast_agent,
            script_generator_agent=script_generator_agent,
            image_generation_agent=image_generation_agent,
            router_agent=router_agent,
            sub_agents=sub_agents_list,
            chroma_manager=chroma_manager,
            link_processor=link_processor
        )

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        logger.info(f"[{self.name}] Starting enhanced multimodal processing workflow.")
        logger.info(f"[{self.name}] Running Router Agent...")
        
        try:
            async for event in self.router_agent.run_async(ctx):
                logger.info(f"[{self.name}] Event from Router: {event.model_dump_json(indent=2, exclude_none=True)}")
                yield event
        except Exception as e:
            logger.error(f"[{self.name}] Error in router agent: {str(e)}")
            error_response = f"Error: Router agent failed: {str(e)}"
            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=error_response)]
                ),
                author=self.name
            )
            return

        routing_text = ctx.session.state.get("routing_decision", "")
        if not routing_text:
            logger.error(f"[{self.name}] No routing decision found. Aborting workflow.")
            error_response = "Error: No routing decision available."
            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=error_response)]
                ),
                author=self.name
            )
            return

        try:
            json_match = re.search(r'\{.*\}', routing_text, re.DOTALL)
            if json_match:
                routing_data = json.loads(json_match.group())
                routing_decision = RoutingDecision(**routing_data)
            else:
                raise ValueError("No valid JSON found in routing decision")
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse routing decision JSON: {e}")
            routing_decision = RoutingDecision(
                content_types=["text"],
                primary_agent="text",
                requires_multimodal=False,
                processing_plan="Process as text query",
                instructions="Provide a comprehensive response"
            )

        logger.info(f"[{self.name}] Routing decision: {routing_decision.model_dump()}")
        ctx.session.state["parsed_routing_decision"] = routing_decision.model_dump()
        if routing_decision.audio_config:
            ctx.session.state["audio_config"] = routing_decision.audio_config

        agent_map = {
            "text": self.text_agent,
            "image": self.image_agent,
            "video": self.video_agent,
            "audio": self.audio_agent,
            "realtime_audio": self.realtime_audio_agent,
            "podcast": self.podcast_agent,
            "script_generator": self.script_generator_agent,
            "image_generation": self.image_generation_agent
        }

        primary_agent = agent_map.get(routing_decision.primary_agent, self.text_agent)
        ctx.session.state["processing_instructions"] = routing_decision.instructions
        
        logger.info(f"[{self.name}] Running {primary_agent.name}...")
        try:
            async for event in primary_agent.run_async(ctx):
                logger.info(f"[{self.name}] Event from {primary_agent.name}: {event.model_dump_json(indent=2, exclude_none=True)}")
                yield event
        except Exception as e:
            logger.error(f"[{self.name}] Error in {primary_agent.name}: {str(e)}")
            error_response = f"Error: {primary_agent.name} failed: {str(e)}"
            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=error_response)]
                ),
                author=self.name
            )

        if routing_decision.primary_agent == "podcast" and not ctx.session.state.get("podcast_script"):
            logger.info(f"[{self.name}] No script found for podcast generation. Generating script first.")
            ctx.session.state["processing_instructions"] = "Generate an engaging podcast script based on the provided topic"
            try:
                async for event in self.script_generator_agent.run_async(ctx):
                    logger.info(f"[{self.name}] Event from ScriptGeneratorAgent: {event.model_dump_json(indent=2, exclude_none=True)}")
                    yield event
            except Exception as e:
                logger.error(f"[{self.name}] Error in ScriptGeneratorAgent: {str(e)}")
                error_response = f"Error: Script generation failed: {str(e)}"
                yield Event(
                    content=types.Content(
                        role='assistant',
                        parts=[types.Part(text=error_response)]
                    ),
                    author=self.name
                )

        if ctx.session.state.get("podcast_script"):
            logger.info(f"[{self.name}] Triggering podcast generation with generated script.")
            ctx.session.state["processing_instructions"] = "Convert the generated script into spoken audio"
            try:
                async for event in self.podcast_agent.run_async(ctx):
                    logger.info(f"[{self.name}] Event from PodcastGeneratorAgent: {event.model_dump_json(indent=2, exclude_none=True)}")
                    yield event
            except Exception as e:
                logger.error(f"[{self.name}] Error in PodcastGeneratorAgent: {str(e)}")
                error_response = f"Error: Podcast generation failed: {str(e)}"
                yield Event(
                    content=types.Content(
                        role='assistant',
                        parts=[types.Part(text=error_response)]
                    ),
                    author=self.name
                )

        logger.info(f"[{self.name}] Enhanced multimodal workflow completed.")

    @override
    async def _run_live_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        logger.info(f"[{self.name}] Starting live session.")
        try:
            welcome_message = """
🎬 **Multimodal Orchestrator Live Session Started**

I'm ready to help you with:
- 📝 Podcast script generation
- 🎙️ Podcast audio generation
- 🖼️ Image generation
- 🎵 Audio analysis and processing
- 🖼️ Image analysis and understanding
- 📊 Data visualization and insights
- 🤖 Real-time multimodal workflows

Send me your files or messages, and I'll coordinate the appropriate specialized agents!
            """.strip()
            
            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=welcome_message)]
                ),
                author=self.name
            )
            
            while True:
                if hasattr(ctx, 'content') and ctx.content:
                    async for event in self._run_async_impl(ctx):
                        yield event
                    break
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"[{self.name}] Error in live session: {e}")
            error_message = f"❌ Live session error: {str(e)}"
            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=error_message)]
                ),
                author=self.name
            )

# --- Define Individual LLM Agents ---
enhanced_router_instruction = """
You are an enhanced routing agent that determines how to process user requests including podcast script, audio generation, and image generation.

Analyze the user input and respond with a JSON object:
{
    "content_types": ["list of content types"],
    "processing_plan": "description of processing approach",
    "requires_multimodal": true/false,
    "primary_agent": "main agent to use",
    "instructions": "specific instructions",
    "audio_config": {"realtime": true/false, "sample_rate": 16000}
}

Content types: text, image, audio, video, realtime_audio, speech_generation, image_generation, script_generation

Primary agents (must match exactly): text, image, video, audio, realtime_audio, podcast, script_generator, image_generation

SCRIPT GENERATION RULES:
- Requests containing "generate podcast script", "create podcast script" should use:
  - content_types: ["script_generation"]
  - primary_agent: "script_generator"
  - instructions: "Generate an engaging podcast script based on the provided topic"

PODCAST GENERATION RULES:
- Requests containing "generate podcast", "convert to audio", "create podcast", "make podcast", "podcast" should use:
  - content_types: ["speech_generation"]
  - primary_agent: "podcast"
  - instructions: "Convert the provided text into engaging spoken audio using ElevenLabs TTS"

IMAGE GENERATION RULES:
- Requests containing "generate image", "create image", "render image" should use:
  - content_types: ["image_generation"]
  - primary_agent: "image_generation"
  - instructions: "Generate an image using the provided description"

OTHER ROUTING RULES:
- "real-time audio", "live audio", "stream audio" -> realtime_audio
- URLs ending in .mp3, .wav, .m4a, .aac -> audio
- URLs ending in .jpg, .png, .gif, .jpeg -> image
- URLs with youtube.com, youtu.be, or ending in .mp4, .avi -> video
- Default to text for questions and discussions

IMPORTANT: For script generation, store the script in session state under 'podcast_script'. For podcast generation, check 'podcast_script' first. For image generation, store the image metadata in session state under 'generated_image'.
"""

enhanced_router_agent = LlmAgent(
    name="RouterAgent",
    model=MODEL_GEMINI_FLASH,
    instruction=enhanced_router_instruction,
    input_schema=None,
    output_key="routing_decision"
)

# --- Setup Session and Runner ---
session_service = InMemorySessionService()
initial_state = {"conversation_history": [], "input_text": "", "podcast_script": "", "generated_image": {}}

text_agent = LlmAgent(
    name="TextAnalysisAgent",
    model=MODEL_GEMINI_2_FLASH,
    instruction="""
    You are a text analysis agent. Analyze and respond to text queries comprehensively.
    
    Use any processing instructions provided in the session state under 'processing_instructions'.
    Provide detailed, helpful responses to user queries.
    """,
    input_schema=None,
    output_key="text_analysis_result"
)

image_agent = LlmAgent(
    name="ImageAnalysisAgent",
    model=MODEL_GEMINI_2_FLASH,
    instruction="""
    You are an image analysis agent. Analyze images in detail and describe their contents.
    
    Use any processing instructions provided in the session state under 'processing_instructions'.
    If you receive a URL, treat it as an image URL and provide analysis based on what would typically be found at such URLs.
    
    Provide detailed descriptions including:
    - Visual elements and composition
    - Colors, lighting, and mood
    - Objects, people, or scenes present
    - Any text or symbols visible
    """,
    input_schema=None,
    output_key="image_analysis_result"
)

video_agent = LlmAgent(
    name="VideoAnalysisAgent",
    model=MODEL_GEMINI_2_FLASH,
    instruction="""
    You are a video analysis agent. Analyze video content and describe what you observe.
    
    Use any processing instructions provided in the session state under 'processing_instructions'.
    If you receive a URL, provide analysis based on what would typically be found in videos from such URLs.
    
    Provide comprehensive analysis including:
    - Content summary and main topics
    - Visual elements and production quality
    - Audio elements if applicable
    - Key moments or highlights
    - Overall structure and flow
    """,
    input_schema=None,
    output_key="video_analysis_result"
)

audio_agent = LlmAgent(
    name="AudioAnalysisAgent",
    model=MODEL_GEMINI_2_FLASH,
    instruction="""
    You are an audio analysis agent. Analyze audio content and transcribe or describe it.
    
    Use any processing instructions provided in the session state under 'processing_instructions'.
    
    Provide comprehensive analysis including:
    - Transcription of speech content
    - Audio quality assessment
    - Background sounds or music identification
    - Speaker identification if multiple voices
    - Emotional tone and delivery style
    - Technical audio properties (sample rate, format, etc.)
    
    If processing pre-recorded audio files, provide detailed analysis.
    For real-time audio, defer to the RealtimeAudioAgent.
    """,
    input_schema=None,
    output_key="audio_analysis_result"
)

realtime_audio_agent = RealtimeAudioAgent()
podcast_agent = PodcastGeneratorAgent()
script_generator_agent = ScriptGeneratorAgent()
image_generation_agent = ImageGenerationAgent()

# --- Create the Enhanced Orchestrator Agent Instance ---
multimodal_orchestrator = MultimodalOrchestratorAgent(
    name="MultimodalOrchestratorAgent",
    text_agent=text_agent,
    image_agent=image_agent,
    video_agent=video_agent,
    audio_agent=audio_agent,
    realtime_audio_agent=realtime_audio_agent,
    podcast_agent=podcast_agent,
    script_generator_agent=script_generator_agent,
    image_generation_agent=image_generation_agent,
    router_agent=enhanced_router_agent
)

# --- Setup Session and Runner ---
session_service = InMemorySessionService()
initial_state = {"conversation_history": [], "input_text": "", "podcast_script": "", "generated_image": {}}

runner = Runner(
    agent=multimodal_orchestrator,
    app_name=APP_NAME,
    session_service=session_service
)

async def initialize_session():
    try:
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
            state=initial_state
        )
        logger.info(f"Initial session state: {session.state}")
        logger.info(f"Session object type: {type(session)} value: {session}")
        print(f"[DEBUG] Initial session state: {session.state}")
        print(f"[DEBUG] Session object type: {type(session)} value: {session}")
        return session
    except Exception as e:
        logger.error(f"Exception in initialize_session: {e}")
        print(f"[DEBUG] Exception in initialize_session: {e}")
        return None

async def call_agent(query: str, audio_file_path: Optional[str] = None):
    try:
        current_session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID
        )
        logger.info(f"call_agent: get_session returned type: {type(current_session)} value: {current_session}")
        print(f"[DEBUG] call_agent: get_session returned type: {type(current_session)} value: {current_session}")
        
        if not current_session:
            logger.warning("Session not found, creating new one")
            print("[DEBUG] Session not found, creating new one")
            current_session = await initialize_session()
            if not current_session:
                logger.error("Failed to get or create session! (call_agent)")
                print("[DEBUG] Failed to get or create session! (call_agent)")
                return "Error: Could not initialize session"

        current_session.state["input_text"] = query
        if audio_file_path:
            current_session.state["audio_file_path"] = audio_file_path

        content = types.Content(role='user', parts=[types.Part(text=query)])
        events = runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)

        final_response = "No final response captured."
        for event in events:
            if event.is_final_response() and event.content and event.content.parts:
                logger.info(f"Final response from [{event.author}]: {event.content.parts[0].text}")
                final_response = event.content.parts[0].text

        print("\n--- Enhanced Multimodal Agent Response ---")
        print("Agent Final Response:", final_response)

        try:
            final_session = await session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID
            )
            if final_session:
                print("\nFinal Session State:")
                print(json.dumps(final_session.state, indent=2))
        except Exception as e:
            logger.warning(f"Could not retrieve final session state: {e}")
        
        print("------------------------------------------\n")
        return final_response
    except Exception as e:
        logger.error(f"Error in call_agent: {e}")
        return f"Error: {str(e)}"

# --- Enhanced Interactive Interface ---
class MultimodalAgentInterface:
    def __init__(self):
        self.session_service = session_service
        self.runner = runner
        self.podcast_agent = PodcastGeneratorAgent()
        self.chroma_manager = ChromaDBManager(
            podcast_agent=self.podcast_agent,
            text_agent=text_agent,
            image_generation_agent=image_generation_agent
        )
        self.link_processor = LinkProcessor(self.chroma_manager)

    async def chat(self, query: str, audio_file_path: Optional[str] = None) -> str:
        return await call_agent(query, audio_file_path)

    async def process_audio_file(self, audio_file_path: str, query: str = "Analyze this audio file") -> str:
        if not os.path.exists(audio_file_path):
            return f"Error: Audio file not found at {audio_file_path}"
        return await self.chat(query, audio_file_path)

    async def start_realtime_audio(self, query: str = "Start real-time audio processing") -> str:
        return await self.chat(f"real-time audio: {query}")

    async def generate_podcast(self, text: str) -> str:
        try:
            session = await self.session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID
            )
            if not session:
                session = await self.session_service.create_session(
                    app_name=APP_NAME,
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    state={"conversation_history": [], "input_text": "", "podcast_script": "", "generated_image": {}}
                )

            session.state["input_text"] = text
            logger.info(f"Stored input_text in session state: {text[:50]}{'...' if len(text) > 50 else ''}")

            podcast_query = f"Generate a podcast from this text: {text}"
            content = types.Content(role='user', parts=[types.Part(text=podcast_query)])
            events = self.runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)

            final_response = "No response captured."
            for event in events:
                if event.is_final_response() and event.content and event.content.parts:
                    logger.info(f"[{event.author}]: {event.content.parts[0].text}")
                    final_response = event.content.parts[0].text

            return final_response
            
        except Exception as e:
            logger.error(f"Error generating podcast: {str(e)}")
            return f"Error: {str(e)}"

    async def generate_podcast_script(self, topic: str) -> str:
        try:
            session = await self.session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID
            )
            if not session:
                session = await self.session_service.create_session(
                    app_name=APP_NAME,
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    state={"conversation_history": [], "input_text": "", "podcast_script": "", "generated_image": {}}
                )
            
            session.state["input_text"] = f"Generate a podcast script about {topic}"
            session.state["podcast_script"] = ""
            logger.info(f"Stored topic in session state: {topic[:50]}{'...' if len(topic) > 50 else ''}")
            
            script_query = f"Generate a podcast script about {topic}"
            content = types.Content(role='user', parts=[types.Part(text=script_query)])
            events = self.runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)
            
            final_response = "No response captured."
            for event in events:
                if event.is_final_response() and event.content and event.content.parts:
                    logger.info(f"[{event.author}]: {event.content.parts[0].text}")
                    final_response = event.content.parts[0].text
            
            return final_response
        except Exception as e:
            logger.error(f"Error generating podcast script: {str(e)}")
            return f"Error: {str(e)}"

    async def generate_image(self, description: str) -> str:
        try:
            session = await self.session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID
            )
            if not session:
                session = await self.session_service.create_session(
                    app_name=APP_NAME,
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    state={"conversation_history": [], "input_text": "", "podcast_script": "", "generated_image": {}}
                )

            session.state["input_text"] = f"Generate an image of {description}"
            logger.info(f"Stored image description in session state: {description[:50]}{'...' if len(description) > 50 else ''}")

            content = types.Content(role='user', parts=[types.Part(text=f"Generate an image of {description}")])
            events = self.runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)

            final_response = "No response captured."
            for event in events:
                if event.is_final_response() and event.content and event.content.parts:
                    logger.info(f"[{event.author}]: {event.content.parts[0].text}")
                    final_response = event.content.parts[0].text

            return final_response
        
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            return f"Error: {str(e)}"

    async def get_conversation_history(self) -> List[Dict[str, Any]]:
        try:
            current_session = await self.session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID
            )
            if current_session:
                return current_session.state.get("conversation_history", [])
            return []
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []

    async def clear_history(self):
        try:
            current_session = await self.session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID
            )
            if current_session:
                current_session.state["conversation_history"] = []
        except Exception as e:
            logger.error(f"Error clearing history: {e}")

    async def process_link(self, url: str) -> str:
        try:
            doc_id = self.link_processor.process_link(url)
            if doc_id:
                return f"✅ Link processed successfully. Document ID: {doc_id}"
            return "❌ Failed to process link"
        except Exception as e:
            return f"❌ Error processing link: {str(e)}"

    async def search_stored_data(self, query: str) -> str:
        try:
            results = self.chroma_manager.search_similar(query)
            if results:
                return "\n".join([f"📄 {doc['id']}: {doc['content'][:100]}..." for doc in results])
            return "No matching documents found"
        except Exception as e:
            return f"❌ Error searching data: {str(e)}"

    async def list_stored_data(self) -> str:
        try:
            results = self.chroma_manager.get_all_documents()
            if results:
                return "\n".join([f"📄 {doc['id']}: {doc['url']}" for doc in results])
            return "No documents stored"
        except Exception as e:
            return f"❌ Error listing data: {str(e)}"

    async def generate_summary(self, doc_ids: List[str]) -> str:
        try:
            return await self.chroma_manager.generate_summary(doc_ids)
        except Exception as e:
            return f"❌ Error generating summary: {str(e)}"

    async def generate_podcast_from_data(self, doc_ids: List[str]) -> str:
        try:
            return await self.chroma_manager.generate_podcast(doc_ids)
        except Exception as e:
            return f"❌ Error generating podcast: {str(e)}"

    async def generate_image_from_data(self, doc_ids: List[str]) -> str:
        try:
            return await self.chroma_manager.generate_image(doc_ids)
        except Exception as e:
            return f"❌ Error generating image: {str(e)}"

    async def interactive_mode(self):
        print("🤖 Enhanced Multimodal AI Agent System")
        print("=" * 70)
        print("Available capabilities:")
        print("- Text processing and analysis")
        print("- Audio file processing")
        print("- Real-time audio processing")
        print("- Podcast generation")
        print("- Podcast script generation")
        print("- Image generation")
        print("- Link processing and storage")
        print("- Data retrieval and analysis")
        print("=" * 70)
        print("\nSpecial commands for link processing:")
        print("- process <url> - Process and store a link")
        print("- search <query> - Search stored data")
        print("- list - List all stored documents")
        print("- summary <doc_id1,doc_id2,...> - Generate summary from documents")
        print("- podcast <doc_id1,doc_id2,...> - Generate podcast from documents")
        print("- image <doc_id1,doc_id2,...> - Generate image from documents")
        print("=" * 70)

        while True:
            try:
                user_input = input("\nYou: ").strip()

                if user_input.lower() == "exit":
                    print("Goodbye! 👋")
                    break
                elif not user_input:
                    print("❌ Please enter a query.")
                    continue

                if user_input.startswith("process "):
                    url = user_input[8:].strip()
                    response = await self.process_link(url)
                elif user_input.startswith("search "):
                    query = user_input[7:].strip()
                    response = await self.search_stored_data(query)
                elif user_input.lower() == "list":
                    response = await self.list_stored_data()
                elif user_input.startswith("summary "):
                    doc_ids = user_input[8:].strip().split(",")
                    response = await self.generate_summary(doc_ids)
                elif user_input.startswith("podcast "):
                    doc_ids = user_input[8:].strip().split(",")
                    response = await self.generate_podcast_from_data(doc_ids)
                elif user_input.startswith("image "):
                    doc_ids = user_input[6:].strip().split(",")
                    response = await self.generate_image_from_data(doc_ids)
                else:
                    print("\n🔄 Processing...")
                    response = await self.chat(user_input)
                
                print(f"\n🤖 Response:")
                print(f"{response}")

            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {str(e)}")
                logger.error(f"Unexpected error in interactive mode: {str(e)}")

# --- Audio Utilities for External Use ---
class AudioUtils:
    @staticmethod
    def validate_audio_file(file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {"valid": False, "error": "File not found"}
        
        try:
            audio = AudioSegment.from_file(file_path)
            info = {
                "valid": True,
                "sample_rate": audio.frame_rate,
                "channels": audio.channels,
                "sample_width": audio.sample_width,
                "frames": audio.frame_count(),
                "duration": len(audio) / 1000.0
            }
            return info
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    @staticmethod
    def create_test_audio_config() -> AudioConfig:
        return AudioConfig(
            sample_rate=16000,
            bit_depth=16,
            channels=1,
            format="pcm",
            realtime=False
        )
    
    @staticmethod
    def download_sample_audio(url: str = "https://storage.googleapis.com/generativeai-downloads/data/16000.wav", 
                            output_path: str = "sample.wav") -> bool:
        try:
            import urllib.request
            urllib.request.urlretrieve(url, output_path)
            return True
        except Exception as e:
            logger.error(f"Failed to download sample audio: {e}")
            return False

# --- API-like Functions for Integration ---
class MultimodalAPI:
    def __init__(self):
        self.interface = MultimodalAgentInterface()
        self.audio_processor = AudioProcessor()
    
    def process_text(self, text: str) -> Dict[str, Any]:
        try:
            response = self.interface.chat(text)
            return {
                "success": True,
                "response": response,
                "type": "text",
                "timestamp": str(asyncio.get_event_loop().time())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "type": "text"
            }
    
    def process_audio_file(self, file_path: str, instructions: str = "Analyze this audio") -> Dict[str, Any]:
        try:
            validation = AudioUtils.validate_audio_file(file_path)
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": validation["error"],
                    "type": "audio"
                }
            response = self.interface.process_audio_file(file_path, instructions)
            return {
                "success": True,
                "response": response,
                "type": "audio",
                "file_info": validation,
                "timestamp": str(asyncio.get_event_loop().time())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "type": "audio"
            }
    
    def start_realtime_audio_session(self, config: Optional[AudioConfig] = None) -> Dict[str, Any]:
        try:
            if config is None:
                config = AudioUtils.create_test_audio_config()
                config.realtime = True
            response = self.interface.start_realtime_audio()
            return {
                "success": True,
                "response": response,
                "type": "realtime_audio",
                "config": config.dict(),
                "timestamp": str(asyncio.get_event_loop().time())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "type": "realtime_audio"
            }
    
    def generate_podcast(self, text: str) -> Dict[str, Any]:
        try:
            response = self.interface.generate_podcast(text)
            return {
                "success": True,
                "response": response,
                "type": "speech_generation",
                "timestamp": str(asyncio.get_event_loop().time())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "type": "speech_generation"
            }
    
    def generate_podcast_script(self, topic: str) -> Dict[str, Any]:
        try:
            response = self.interface.generate_podcast_script(topic)
            return {
                "success": True,
                "response": response,
                "type": "script_generation",
                "timestamp": str(asyncio.get_event_loop().time())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "type": "script_generation"
            }
    
    def generate_image(self, description: str) -> Dict[str, Any]:
        try:
            response = self.interface.generate_image(description)
            return {
                "success": True,
                "response": response,
                "type": "image_generation",
                "timestamp": str(asyncio.get_event_loop().time())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "type": "image_generation"
            }
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        return {
            "audio": [".wav", ".mp3", ".m4a", ".aac"],
            "video": [".mp4", ".avi", ".mov", ".mkv"],
            "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
            "text": ["plain text", "markdown", "json"],
            "speech_generation": ["text"],
            "script_generation": ["text"],
            "image_generation": ["text"]
        }

# --- Configuration and Setup Helpers ---
def setup_audio_environment():
    try:
        import pydub
        logger.info("Audio processing libraries available")
        audio_dir = Path("audio_samples")
        audio_dir.mkdir(exist_ok=True)
        sample_path = audio_dir / "sample.wav"
        if not sample_path.exists():
            if AudioUtils.download_sample_audio(output_path=str(sample_path)):
                logger.info(f"Downloaded sample audio to {sample_path}")
            else:
                logger.warning("Could not download sample audio file")
        return True
    except ImportError as e:
        logger.error(f"Missing required audio libraries: {e}")
        return False

def get_system_info() -> Dict[str, Any]:
    return {
        "agents": {
            "text": "TextAnalysisAgent",
            "image": "ImageAnalysisAgent",
            "video": "VideoAnalysisAgent",
            "audio": "AudioAnalysisAgent",
            "realtime_audio": "RealtimeAudioAgent",
            "podcast": "PodcastGeneratorAgent",
            "script_generator": "ScriptGeneratorAgent",
            "image_generation": "ImageGenerationAgent"
        },
        "models": {
            "primary": MODEL_GEMINI_2_FLASH,
            "router": MODEL_GEMINI_FLASH,
            "live": MODEL_GEMINI_LIVE,
            "image_generation": MODEL_IMAGE_GENERATION
        },
        "audio_config": {
            "sample_rate": AUDIO_SAMPLE_RATE,
            "bit_depth": AUDIO_BIT_DEPTH,
            "channels": AUDIO_CHANNELS
        },
        "supported_formats": MultimodalAPI().get_supported_formats()
    }

# --- Export root agent ---
root_agent = multimodal_orchestrator

async def main():
    try:
        print('[DEBUG] Entered __main__')
        
        # Initialize session before starting interface
        session = await initialize_session()
        if not session:
            print("Error: Failed to initialize session.")
            sys.exit(1)

        interface = MultimodalAgentInterface()
        await interface.interactive_mode()

        sys.exit(0)
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())