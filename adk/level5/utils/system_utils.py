import logging
from pathlib import Path
from typing import Dict, Any
from level5.constants_and_models import MODEL_GEMINI_2_FLASH, MODEL_GEMINI_FLASH, MODEL_GEMINI_LIVE, MODEL_IMAGE_GENERATION, AUDIO_SAMPLE_RATE, AUDIO_BIT_DEPTH, AUDIO_CHANNELS
from level5.utils.audio_utils import AudioUtils

logger = logging.getLogger(__name__)



"""This module provides configuration and setup helpers for the Level 5 multimodal agent system."""
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




"""This module provides a function to retrieve system information, including available agents, models, audio configuration, and supported formats."""
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
        "supported_formats": {
            "audio": [".wav", ".mp3", ".m4a", ".aac"],
            "video": [".mp4", ".avi", ".mov", ".mkv"],
            "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
            "text": ["plain text", "markdown", "json"],
            "speech_generation": ["text"],
            "script_generation": ["text"],
            "image_generation": ["text"]
        }
    }