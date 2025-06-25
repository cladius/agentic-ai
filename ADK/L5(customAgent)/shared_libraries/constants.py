"""
Constants used across the multimodal agent system
"""

# Model names
# Model names - Updated with correct format
MODEL_GEMINI_FLASH = "gemini-1.5-flash"
MODEL_GEMINI_2_FLASH = "gemini-2.0-flash"
MODEL_GEMINI_2_FLASH_EXP = "gemini-2.0-flash-exp"
MODEL_GEMINI_TTS = "gemini-2.5-flash-preview-tts"
MODEL_GEMINI_2_FLASH_IMAGE_GEN = "gemini-2.0-flash-preview-image-generation"

# Agent names
AGENT_NAME = "multimodal_agent"
TEXT_ANALYSIS_AGENT = "text_analysis_agent"
IMAGE_ANALYSIS_AGENT = "image_analysis_agent"
AUDIO_ANALYSIS_AGENT = "audio_analysis_agent"
VIDEO_ANALYSIS_AGENT = "video_analysis_agent"
SPEECH_GENERATION_AGENT = "speech_generation_agent"
IMAGE_GENERATION_AGENT = "image_generation_agent"

# Agent descriptions
DESCRIPTION = "A multimodal agent system that can analyze and generate various types of content."

# Content types
class ContentType:
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    SPEECH_GENERATION = "speech_generation"
    IMAGE_GENERATION = "image_generation"
    NEWS_SEARCH = "news_search"
    MULTIMODAL_ANALYSIS = "multimodal_analysis"

# Application name
APP_NAME = "multimodal_agent_app" 