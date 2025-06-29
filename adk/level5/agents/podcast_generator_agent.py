
import logging
from pydantic import BaseModel, Field
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types
from elevenlabs.client import ElevenLabs
from pathlib import Path
from datetime import datetime
import os
import re
from typing import AsyncGenerator, List, Dict, Any

logger = logging.getLogger(__name__)

# --- Constants from constants_and_models.py ---
MODEL_GEMINI_2_FLASH = "gemini-2.0-flash-exp"

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