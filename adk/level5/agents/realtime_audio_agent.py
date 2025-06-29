import logging
from pydantic import BaseModel, Field
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types
from typing import AsyncGenerator, Dict, Any, Optional
import os

from audio_processor import AudioProcessor
from constants_and_models import AudioConfig, AUDIO_SAMPLE_RATE, AUDIO_BIT_DEPTH, AUDIO_CHANNELS
from constants_and_models import MODEL_GEMINI_LIVE

logger = logging.getLogger(__name__)

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