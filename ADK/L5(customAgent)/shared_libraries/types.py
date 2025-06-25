from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
from google.adk.agents.llm_agent import Agent

class ContentType(Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    SPEECH_GENERATION = "speech_generation"
    NEWS_SEARCH = "news_search"
    MULTIMODAL_ANALYSIS = "multimodal_analysis"
    IMAGE_GENERATION = "image_generation"

@dataclass
class AgentResponse:
    content: str
    metadata: Dict[str, Any]
    success: bool
    agent_name: str
    error_message: Optional[str] = None

class BaseSubAgent(ABC):
    """Base class for all sub-agents"""
    
    def __init__(self, name: str, model: str = "gemini-2.0-flash"):
        self.name = name
        self.model = model
        self.client = None  # Will be initialized by subclasses
        
    @abstractmethod
    async def process(self, content: Any, instructions: str = "") -> AgentResponse:
        pass 