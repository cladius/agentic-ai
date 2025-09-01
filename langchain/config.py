import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your-groq-api-key")
    MODEL_NAME = os.getenv("MODEL_NAME", "llama3-8b-8192")

# Optionally, you can load from a .env file or other config sources
