from pydantic import BaseModel
from typing import List
import logfire

class UserInput(BaseModel):
    question: str

class AgentResponse(BaseModel):
    response: str
    conversation_history: List[str]