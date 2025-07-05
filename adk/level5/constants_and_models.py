import logging
import os
from dotenv import load_dotenv
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from pathlib import Path


""" This module provides constants, configuration, and models for the Level 5 multimodal agent system, including routing decisions, agent responses, and audio configurations."""
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
INITIAL_STATE = {
    "conversation_history": [],
    "input_text": "",
    "podcast_script": "",
    "generated_image": {},
    "last_processed_document_id": None
}


# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Load Environment Variables ---
# Get the directory where this file is located
current_dir = Path(__file__).parent
load_dotenv(current_dir / ".env")


"""Ensure required environment variables are set for API keys."""
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



"""This module defines the data models used in the Level 5 multimodal agent system, including routing decisions and agent responses."""
class RoutingDecision(BaseModel):
    content_types: List[str] = Field(default_factory=list)
    processing_plan: str = ""
    requires_multimodal: bool = False
    primary_agent: str = "text"
    instructions: str = ""
    audio_config: Optional[Dict[str, Any]] = None



"""This module defines the response model for agents in the Level 5 multimodal agent system, including content, metadata, success status, and error messages."""
class AgentResponse(BaseModel):
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    agent_name: str = ""
    error_message: Optional[str] = None


"""This module defines the audio configuration model used in the Level 5 multimodal agent system, 
including sample rate, bit depth, channels, format, and realtime processing options."""


class AudioConfig(BaseModel):
    sample_rate: int = AUDIO_SAMPLE_RATE
    bit_depth: int = AUDIO_BIT_DEPTH
    channels: int = AUDIO_CHANNELS
    format: str = "pcm"
    realtime: bool = False