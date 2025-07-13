import os
import asyncio
import json # Import json for reading/writing structured data
from pydantic import BaseModel, Field
from pydantic_ai import Tool
from elevenlabs import ElevenLabs 
import logfire
import uuid

class AudioInput(BaseModel):
    script_file: str = Field(description="Path to the JSON script file for audio generation (containing text and speaker info).")
    output_file: str = Field(description="Path where the generated audio file should be saved (e.g., podcast.mp3).")

def create_script_generation_tool() -> Tool:
    async def generate_script(summary: str, output_file: str) -> str:
        """
        Generates a structured podcast script (JSON) from a summary with a conversational style for two speakers,
        and saves it to a file. This version generates a much shorter script (max ~7 content sentences).
        """
        try:
            sentences = [s.strip() for s in summary.split('.') if s.strip()]
            
            # This list will store dictionaries of {"text": "...", "speaker": "A/B"}
            structured_script_data = []
            
            if not sentences:
                structured_script_data.append({"text": "Welcome to our podcast! Today, we're exploring a very brief topic.", "speaker": "A"})
                structured_script_data.append({"text": "Indeed. Thanks for listening!", "speaker": "B"})
            else:
                # Select only the most important sentences for a short script
                # Taking the first few, a middle one, and the last one to capture key points
                selected_sentences = []
                if len(sentences) >= 1:
                    selected_sentences.append(sentences[0]) # Opening
                if len(sentences) >= 2:
                    selected_sentences.append(sentences[1]) # Second important point
                if len(sentences) >= 3:
                    selected_sentences.append(sentences[len(sentences) // 2]) # A middle point
                if len(sentences) >= 4:
                    selected_sentences.append(sentences[-1]) # Concluding point
                
                # Ensure no more than 6-7 actual content sentences for brevity and credit limits
                # This explicitly limits the number of sentences that will be spoken by the hosts.
                selected_sentences = selected_sentences[:7] 

                # Build the structured script data with speaker assignments
                if selected_sentences:
                    structured_script_data.append({"text": f"Welcome to our podcast! Today, we're diving into a quick look at: {selected_sentences[0]}", "speaker": "A"})
                    
                    if len(selected_sentences) > 1:
                        structured_script_data.append({"text": f"That's right. Let's briefly discuss {selected_sentences[1]}.", "speaker": "B"})
                    
                    if len(selected_sentences) > 2:
                        structured_script_data.append({"text": f"A crucial aspect to note is {selected_sentences[2]}.", "speaker": "A"})
                    
                    if len(selected_sentences) > 3:
                        structured_script_data.append({"text": f"And let's not forget {selected_sentences[3]}.", "speaker": "B"})

                    # Always add concluding remarks
                    final_core_message = selected_sentences[-1] if selected_sentences else "that this information is vital for understanding current trends."
                    structured_script_data.append({"text": f"Indeed. The core message here is {final_core_message}", "speaker": "A"})
                    structured_script_data.append({"text": "Absolutely. Thanks for joining us today for this brief overview.", "speaker": "B"})
                    structured_script_data.append({"text": "Goodbye everyone!", "speaker": "A"})
                else:
                    # Fallback for very short summaries
                    structured_script_data.append({"text": "Welcome to our podcast! We have a very brief topic today.", "speaker": "A"})
                    structured_script_data.append({"text": "Indeed. Thanks for listening!", "speaker": "B"})


            # Save the structured data as a JSON file
            # The output_file should now have a .json extension
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
        description="Generates a structured podcast script (JSON) from a summary, assigning lines to two speakers for short podcasts (max ~7 key sentences).",
        function=generate_script,
    )

def create_audio_generation_tool(elevenlabs_api_key: str) -> Tool[AudioInput]:
    """
    Creates a tool to generate audio from a structured JSON script using ElevenLabs,
    assigning distinct voices to different speakers.
    """
    client = None
    try:
        client = ElevenLabs(api_key=elevenlabs_api_key)
        logfire.info("ElevenLabs client initialized successfully.")
    except Exception as e:
        logfire.error(f"Failed to initialize ElevenLabs client: {str(e)}")
        async def dummy_generate_audio(input_model: AudioInput) -> str:
            return f"Error: ElevenLabs client initialization failed: {str(e)}. Cannot generate audio."
        return Tool[AudioInput](
            name="generate_podcast_audio",
            description="Generates podcast audio from a structured JSON script file using ElevenLabs.",
            function=dummy_generate_audio,
        )

    async def generate_audio(input_model: AudioInput) -> str:
        """
        Generates audio from a structured JSON script file using ElevenLabs and saves it.
        Each sentence is processed with the assigned voice.
        """
        if client is None:
            return "Error: ElevenLabs client not initialized. Cannot generate audio."
            
        # Define the voice IDs for Sarah and Adam
        # Sarah (female) and Adam (male)
        voice_map = {
            "A": "EXAVITQu4vr4xnSDxMaL",  
            "B": "ErXwobaYiN019PkySvjV"    
        }

        try:
            # Read the structured script data from the JSON file
            with open(input_model.script_file, 'r', encoding='utf-8') as f:
                structured_script_data = json.load(f)
            
            # Open the output audio file in binary write mode
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
                    
                    # Generate audio for each sentence with its assigned voice
                    audio_generator = client.text_to_speech.convert(
                        voice_id=voice_id, 
                        text=text_to_speak,
                        model_id="eleven_multilingual_v2" 
                    )
                    
                    # Write the chunks of audio from the generator to the file
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


if __name__ == "__main__":
    async def main():
        elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
        if not elevenlabs_api_key:
            print("Error: ELEVENLABS_API_KEY not set in .env file.")
            print("Please set ELEVENLABS_API_KEY in your .env file to run this example.")
            return

        script_tool = create_script_generation_tool()
        audio_tool = create_audio_generation_tool(elevenlabs_api_key)

        test_summary = "Artificial intelligence (AI) is a field of computer science focused on creating systems capable of performing tasks typically requiring human intelligence, such as learning, reasoning, problem-solving, perception, and decision-making. Its high-profile applications include advanced web search engines, recommendation systems, virtual assistants, autonomous vehicles, and generative AI tools. However, many AI applications are integrated into everyday technology without explicit labeling as 'AI.' AI research is divided into subfields pursuing specific goals and using particular tools. The field involves speech recognition, image classification, facial recognition, object tracking, and robotic perception."
        
        unique_id = str(uuid.uuid4())[:8]
        # Note: The script file will now be .json
        test_script_file = f"test_script_{unique_id}.json" 
        test_audio_file = f"test_podcast_{unique_id}.mp3"

        script_result = await script_tool.function(summary=test_summary, output_file=test_script_file)
        print(script_result)

        if "Error" not in script_result:
            # IMPORTANT: Ensure the script_file path passed to AudioInput is the .json path
            # The script_result string will contain the correct .json path.
            script_json_path = script_result.split("Script saved to ")[1].strip()
            audio_input = AudioInput(script_file=script_json_path, output_file=test_audio_file)
            audio_result = await audio_tool.function(audio_input)
            print(audio_result)
        else:
            print("Skipping audio generation due to script error.")

    asyncio.run(main())