from google.genai import types
from typing import Any



"""This module provides utilities for extracting text from various message formats, including Google GenAI types and dictionaries."""
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