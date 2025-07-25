import os
import asyncio
import json
from pydantic import BaseModel, Field
from pydantic_ai import Tool, Agent
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider
from elevenlabs import ElevenLabs 
import logfire
import uuid

class AudioInput(BaseModel):
    """Pydantic model for audio generation input."""
    script_file: str = Field(description="Path to the JSON script file for audio generation (containing text and speaker info).")
    output_file: str = Field(description="Path where the generated audio file should be saved (e.g., podcast.mp3).")

def create_script_generation_tool() -> Tool:
    """Creates a tool to generate a structured podcast script in JSON format using an AI agent."""
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        logfire.error("GEMINI_API_KEY not set")
        async def dummy_generate_script(summary: str, output_file: str) -> str:
            return "Error: GEMINI_API_KEY not set. Cannot generate podcast script."
        return Tool[dict](
            name="generate_podcast_script",
            description="Generates a structured podcast script (JSON) from a summary, assigning lines to two speakers for short podcasts.",
            function=dummy_generate_script,
        )

    agent = Agent(
        model=GeminiModel('gemini-2.5-pro', provider=GoogleGLAProvider(api_key=gemini_api_key)),
        api_key=gemini_api_key,
        system_prompt=(
            "You are an expert podcast scriptwriter creating engaging, concise scripts for two speakers (Speaker A and Speaker B). "
            "Given a summary, generate a podcast script with 5-7 dialogue lines, alternating between speakers, with a maximum of 7 key sentences. "
            "Start with Speaker A introducing the topic enthusiastically, followed by alternating dialogue that covers key points from the summary. "
            "Conclude with Speaker A summarizing the core message and Speaker B closing the podcast. "
            "Ensure the tone is conversational, engaging, and suitable for a short podcast (1-2 minutes). "
            "Return the script as a JSON array of objects with 'text' (the dialogue) and 'speaker' (A or B) fields, enclosed in triple backticks (```json\n...\n```). "
            "If the summary is empty, create a brief generic script about exploring a topic."
        )
    )

    async def generate_script(summary: str, output_file: str) -> str:
        """
        Generates a concise podcast script in JSON from a summary for two speakers using an AI agent.
        Saves the script to a file and returns the file path or error message.
        """
        try:
            prompt = (
                f"Generate a podcast script based on the following summary:\n\n{summary}\n\n"
                "Create a JSON array of 5-7 dialogue lines for two speakers (A and B), alternating between them. "
                "Speaker A starts with an enthusiastic introduction, followed by discussion of key points, and ends with a core message. "
                "Speaker B closes the podcast. Ensure the tone is conversational and engaging. "
                "Return the script as a JSON array in triple backticks (```json\n...\n```)."
            ) if summary.strip() else (
                "Generate a generic podcast script for two speakers (A and B) with 5-7 dialogue lines, "
                "alternating between them, about exploring a brief topic. Speaker A starts with an introduction, "
                "and Speaker B closes the podcast. Return the script as a JSON array in triple backticks (```json\n...\n```)."
            )

            logfire.info(f"Sending prompt to Gemini agent: {prompt[:100]}...")
            response = await agent.run(prompt)
            raw_response = await _extract_response_content(response)
            logfire.info(f"Raw Gemini response: {raw_response[:200]}...")

            # Extract JSON content from triple backticks if present
            if raw_response.startswith('```json') and '```' in raw_response[7:]:
                json_content = raw_response[7:raw_response.rindex('```')].strip()
            else:
                json_content = raw_response

            # Try parsing the response as JSON
            try:
                structured_script_data = json.loads(json_content)
            except json.JSONDecodeError as e:
                logfire.error(f"JSON parsing failed: {str(e)}, raw response: {raw_response}")
                raise ValueError(f"JSON parsing failed: {str(e)}")

            # Validate script format
            if not isinstance(structured_script_data, list) or not all(isinstance(item, dict) and "text" in item and "speaker" in item for item in structured_script_data):
                logfire.error(f"Invalid script format: {structured_script_data}")
                raise ValueError("Invalid script format: Expected a JSON array of objects with 'text' and 'speaker' fields.")

            json_output_file = output_file.replace(".txt", ".json") if output_file.endswith(".txt") else output_file + ".json"
            with open(json_output_file, 'w', encoding='utf-8') as f:
                json.dump(structured_script_data, f, indent=2, ensure_ascii=False)
            
            logfire.info(f"Podcast script (JSON) generated and saved to {json_output_file}")
            return f"Script saved to {json_output_file}"
        except Exception as e:
            logfire.error(f"Error generating script: {str(e)}")
            return f"Error generating script: {str(e)}"

    return Tool[dict](
        name="generate_podcast_script",
        description="Generates a structured podcast script (JSON) from a summary, assigning lines to two speakers for short podcasts using an AI agent.",
        function=generate_script,
    )

async def _extract_response_content(response) -> str:
    """
    Extracts content from an agent's response object.
    Handles various response formats and returns a string.
    """
    try:
        if hasattr(response, 'output'):
            output = response.output
            if isinstance(output, dict):
                for key in ['summary', 'content', 'text', 'output', 'message', 'description']:
                    if key in output and isinstance(output[key], str):
                        return output[key]
                return str(output.get('summary', output.get('description', str(output))))
            elif isinstance(output, str):
                return output
            else:
                return str(output)
        return str(response)
    except Exception as e:
        logfire.error("Failed to extract response content", exc_info=e)
        return f"Error: Failed to extract content: {str(e)}"

def create_audio_generation_tool(elevenlabs_api_key: str) -> Tool[AudioInput]:
    """
    Creates a tool for generating podcast audio from a JSON script using ElevenLabs.
    Assigns distinct voices to speakers and saves the audio file.
    """
    client = None
    try:
        client = ElevenLabs(api_key=elevenlabs_api_key)
        logfire.info("ElevenLabs client initialized successfully.")
    except Exception as e:
        logfire.error(f"Failed to initialize ElevenLabs client: {str(e)}")
        async def dummy_generate_audio(input_model: AudioInput) -> str:
            """Returns an error if ElevenLabs client initialization fails."""
            return f"Error: ElevenLabs client initialization failed: {str(e)}. Cannot generate audio."
        return Tool[AudioInput](
            name="generate_podcast_audio",
            description="Generates podcast audio from a structured JSON script file using ElevenLabs.",
            function=dummy_generate_audio,
        )

    async def generate_audio(input_model: AudioInput) -> str:
        """
        Generates audio from a JSON script using ElevenLabs with assigned voices.
        Saves the audio to a file and returns the file path or error message.
        """
        if client is None:
            return "Error: ElevenLabs client not initialized. Cannot generate audio."
            
        voice_map = {
            "A": "EXAVITQu4vr4xnSDxMaL",  
            "B": "ErXwobaYiN019PkySvjV"    
        }

        try:
            with open(input_model.script_file, 'r', encoding='utf-8') as f:
                structured_script_data = json.load(f)
            
            with open(input_model.output_file, 'wb') as f_audio:
                for item in structured_script_data:
                    text_to_speak = item.get("text", "")
                    speaker = item.get("speaker")

                    if not text_to_speak or not speaker:
                        logfire.warning(f"Skipping malformed script item: {item}")
                        continue

                    voice_id = voice_map.get(speaker)
                    if not voice_id:
                        logfire.warning(f"No voice ID found for speaker {speaker}, skipping item: {item}")
                        continue

                    logfire.info(f"Generating audio for speaker {speaker}: '{text_to_speak[:50]}...'")
                    
                    audio_generator = client.text_to_speech.convert(
                        voice_id=voice_id, 
                        text=text_to_speak,
                        model_id="eleven_multilingual_v2" 
                    )
                    
                    for chunk in audio_generator:
                        if chunk: 
                            f_audio.write(chunk)
            
            abs_output_path = os.path.abspath(input_model.output_file)
            logfire.info(f"Podcast audio saved to {abs_output_path}")
            return f"Podcast audio saved to {abs_output_path}"
        except Exception as e:
            logfire.error(f"Error generating audio: {str(e)}")
            return f"Error generating audio: {str(e)}"

    return Tool[AudioInput](
        name="generate_podcast_audio",
        description="Generates podcast audio from a structured JSON script file using ElevenLabs, with multiple voices.",
        function=generate_audio,
    )