from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

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
    sample_rate: int = 16000
    bit_depth: int = 16
    channels: int = 1
    format: str = "pcm"
    realtime: bool = False 