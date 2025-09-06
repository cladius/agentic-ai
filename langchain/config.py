import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your-groq-api-key")
    MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-oss-20b")

# Optionally, you can load from a .env file or other config sources
