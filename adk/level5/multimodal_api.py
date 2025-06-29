import asyncio
from typing import Dict, Any, List, Optional
from level5.constants_and_models import AudioConfig
from level5.utils import AudioUtils, AudioProcessor
from level5.multimodal_interface import MultimodalAgentInterface

# --- API-like Functions for Integration ---
class MultimodalAPI:
    def __init__(self):
        self.interface = MultimodalAgentInterface()
        self.audio_processor = AudioProcessor()
    
    def process_text(self, text: str) -> Dict[str, Any]:
        try:
            response = asyncio.run(self.interface.chat(text))
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
            response = asyncio.run(self.interface.process_audio_file(file_path, instructions))
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
            response = asyncio.run(self.interface.start_realtime_audio())
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
            response = asyncio.run(self.interface.generate_podcast(text))
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
            response = asyncio.run(self.interface.generate_podcast_script(topic))
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
            response = asyncio.run(self.interface.generate_image(description))
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