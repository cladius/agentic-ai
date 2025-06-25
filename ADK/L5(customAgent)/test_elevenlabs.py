# /Users/sakhiagrawal/Desktop/4/L5(customAgent)/test_elevenlabs.py
from elevenlabs.client import ElevenLabs
import os
from dotenv import load_dotenv

load_dotenv()
client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
audio = client.text_to_speech.convert(
    text="Test",
    voice_id="XB0fDUnXU5powFXDhCwa",  # Charlotte's voice ID
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128"
)
with open("test.mp3", "wb") as f:
    for chunk in audio:
        f.write(chunk)
print("Test MP3 file generated: test.mp3")