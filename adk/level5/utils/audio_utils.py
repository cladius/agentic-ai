import asyncio
import base64
import logging
from pathlib import Path
from typing import Dict, Any
from pydub import AudioSegment

# Try relative imports first (for local development), then absolute imports (for ADK)
try:
    from constants_and_models import AUDIO_SAMPLE_RATE, AUDIO_BIT_DEPTH, AUDIO_CHANNELS, AudioConfig
except ImportError:
    from level5.constants_and_models import AUDIO_SAMPLE_RATE, AUDIO_BIT_DEPTH, AUDIO_CHANNELS, AudioConfig

logger = logging.getLogger(__name__)


"""This module provides utilities for audio processing, including conversion to PCM format,"""
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
            Path(output_path).unlink(missing_ok=True)
            return pcm_data
        except Exception as e:
            logger.error(f"Error processing audio file: {e}")
            raise
    
    
    """Converts raw audio data to a base64-encoded string."""
    @staticmethod
    def audio_to_base64(audio_data: bytes) -> str:
        return base64.b64encode(audio_data).decode('utf-8')
    

    """ Asynchronously processes an audio file to convert it to PCM format and returns a base64-encoded string."""
    @staticmethod
    async def process_audio_file_async(file_path: str) -> str:
        loop = asyncio.get_event_loop()
        audio_data = await loop.run_in_executor(None, AudioProcessor.convert_to_pcm_16khz, file_path)
        return AudioProcessor.audio_to_base64(audio_data)



"""This module provides utilities for audio processing, including conversion to PCM format,"""
# --- Audio Utilities for External Use ---
class AudioUtils:
    @staticmethod
    def validate_audio_file(file_path: str) -> Dict[str, Any]:
        if not Path(file_path).exists():
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
    
    
    
    """Creates a test audio configuration for use in testing or development."""
    @staticmethod
    def create_test_audio_config() -> AudioConfig:
        return AudioConfig(
            sample_rate=16000,
            bit_depth=16,
            channels=1,
            format="pcm",
            realtime=False
        )
    

    """Downloads a sample audio file from a given URL."""
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



""" This module provides utilities for audio processing, including conversion to PCM format,"""
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