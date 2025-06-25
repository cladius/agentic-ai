# list_voices.py
from elevenlabs.client import ElevenLabs
import os
from dotenv import load_dotenv

load_dotenv()
client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
voices = client.voices.get_all()
for voice in voices.voices:
    print(f"Voice Name: {voice.name}, Voice ID: {voice.voice_id}")