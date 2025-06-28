import os
import base64
import time
from dotenv import load_dotenv
from io import BytesIO
from uuid import uuid4
from typing import List, Dict, Optional
from pydub import AudioSegment
from agno.agent import Agent
from agno.workflow.workflow import Workflow
from agno.models.google import Gemini
from agno.tools.eleven_labs import ElevenLabsTools
from agno.utils.log import logger

load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["ELEVEN_LABS_API_KEY"] = os.getenv("ELEVEN_LABS_API_KEY")

# Default voice configurations
VOICE_CONFIGS = {
    "SPEAKER_A": "JBFqnCBsd6RMkjVDRZzb",  # Valid male voice ID
    "SPEAKER_B": "21m00Tcm4TlvDq8ikWAM",  # Valid female voice ID
}

class AudioUtilsWorkflow(Workflow):
    """Workflow to parse, generate, and combine audio segments for a podcast."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.debug(f"Initializing AudioUtilsWorkflow with args: {args}, kwargs: {kwargs}")
        
        # Your voice configs (make sure these IDs are valid)
        self.voice_configs = {
            "SPEAKER_A": "JBFqnCBsd6RMkjVDRZzb",  # Male voice
            "SPEAKER_B": "21m00Tcm4TlvDq8ikWAM",  # Female voice  
        }
        
        # Validate Eleven Labs API key
        api_key = os.getenv("ELEVEN_LABS_API_KEY")
        if not api_key:
            logger.error("ELEVEN_LABS_API_KEY not set.")
            raise ValueError("Missing Eleven Labs API key")
        
        # Create separate agents for each voice - THIS IS KEY
        self.audio_agents = {}
        for speaker, voice_id in self.voice_configs.items():
            try:
                self.audio_agents[speaker] = Agent(
                    name=f"Audio Generator {speaker}",
                    model=Gemini(),
                    tools=[
                        ElevenLabsTools(
                            api_key=api_key,
                            voice_id=voice_id,  # DIFFERENT voice_id for each agent
                            model_id="eleven_multilingual_v2",
                            target_directory="temp_audio"
                        )
                    ],
                    instructions=[
                        "Convert the provided text to speech using the text_to_speech function.",
                        "Use the configured voice for this agent.",
                        "Generate clear, natural-sounding audio."
                    ],
                    debug_mode=True,
                )
                logger.debug(f"Successfully initialized audio agent for {speaker} with voice {voice_id}")
            except Exception as e:
                logger.error(f"Failed to initialize audio agent for {speaker}: {str(e)}", exc_info=True)
                raise

    def parse_conversation_segments(self, conversation: str) -> List[Dict[str, str]]:
        """Parse conversation into sequential segments with speaker identification."""
        segments = []
        lines = conversation.split('\n')
        current_speaker = None
        current_text = ""

        for line in lines:
            line = line.strip()
            if line.startswith("SPEAKER_A:"):
                if current_speaker and current_text.strip():
                    segments.append({
                        'speaker': current_speaker,
                        'text': current_text.strip(),
                        'voice_id': self.voice_configs[current_speaker]
                    })
                current_speaker = "SPEAKER_A"
                current_text = line.replace("SPEAKER_A:", "").strip()
            elif line.startswith("SPEAKER_B:"):
                if current_speaker and current_text.strip():
                    segments.append({
                        'speaker': current_speaker,
                        'text': current_text.strip(),
                        'voice_id': self.voice_configs[current_speaker]
                    })
                current_speaker = "SPEAKER_B"
                current_text = line.replace("SPEAKER_B:", "").strip()
            elif current_speaker and line:
                current_text += " " + line

        if current_speaker and current_text.strip():
            segments.append({
                'speaker': current_speaker,
                'text': current_text.strip(),
                'voice_id': self.voice_configs[current_speaker]
            })

        if not segments:
            logger.error("No valid segments parsed from conversation")
            raise ValueError("No valid segments generated")
        
        logger.debug(f"Parsed {len(segments)} segments: {segments}")
        return segments

    def generate_audio_segment(self, text: str, speaker_name: str) -> bytes:
        """Generate audio for a single segment."""
        logger.info(f"Generating audio for {speaker_name}: {text[:50]}...")
        max_retries = 3
        retry_delay = 2.0
        
        # Use the specific agent for this speaker (each has different voice configured)
        agent = self.audio_agents[speaker_name]  # SPEAKER_A agent vs SPEAKER_B agent
        
        for attempt in range(max_retries):
            try:
                response = agent.run(f"Convert this text to speech: {text}")
                if response.audio and len(response.audio) > 0:
                    audio_data = base64.b64decode(response.audio[0].base64_audio)
                    logger.debug(f"Generated audio for {speaker_name}, length: {len(audio_data)} bytes")
                    time.sleep(5)
                    return audio_data
                else:
                    logger.warning(f"Empty audio response for {speaker_name}, attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"Failed to generate audio for {speaker_name}, attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Failed to generate audio for {speaker_name} after {max_retries} attempts: {str(e)}")
                time.sleep(retry_delay)
        
        raise RuntimeError(f"Failed to generate audio for {speaker_name} after {max_retries} attempts")
    
    def combine_audio_segments(self, audio_segments: List[bytes], output_filename: str) -> str:
        """Combine audio segments with pauses and save as MP3."""
        logger.debug(f"Combining {len(audio_segments)} audio segments")
        if not audio_segments:
            logger.error("No audio segments provided to combine")
            raise ValueError("No segments to combine")

        combined = AudioSegment.empty()
        pause = AudioSegment.silent(duration=500)  # 500ms pause
        
        for i, audio_data in enumerate(audio_segments):
            if not audio_data:
                logger.warning(f"Skipping empty audio segment {i}")
                continue
            try:
                audio_segment = AudioSegment.from_file(BytesIO(audio_data), format="mp3")
                combined += audio_segment
                if i < len(audio_segments) - 1:
                    combined += pause
            except Exception as e:
                logger.error(f"Failed to process audio segment {i}: {str(e)}")
                raise RuntimeError(f"Failed to process audio segment {i}: {str(e)}")

        if not combined:
            logger.error("No valid audio segments were combined")
            raise RuntimeError("No valid audio segments to combine")

        os.makedirs("final_podcast", exist_ok=True)
        output_path = os.path.join("final_podcast", f"{uuid4()}_{output_filename}.mp3")
        logger.info(f"Saving combined audio to {output_path}")
        try:
            combined.export(output_path, format="mp3")
            logger.info(f"Combined audio saved to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to save combined audio to {output_path}: {str(e)}")
            raise RuntimeError(f"Failed to save audio to {output_path}: {str(e)}")

    def run_workflow(self, input_data: Dict[str, str], **kwargs) -> str:
        """Override run_workflow to handle single input dict."""
        logger.debug(f"Running AudioUtilsWorkflow with input: {input_data}, kwargs: {kwargs}")
        
        # Validate input
        if not isinstance(input_data, dict) or 'conversation' not in input_data or 'output_filename' not in input_data:
            logger.error("Invalid input_data: must be a dict with 'conversation' and 'output_filename'")
            raise ValueError("Invalid input_data format")
        
        # Extract parameters
        conversation = input_data['conversation']
        output_filename = input_data['output_filename']
        
        logger.info(f"Processing conversation: {conversation[:50]}..., output_filename: {output_filename}")
        
        # Call the workflow logic directly instead of self.run()
        try:
            segments = self.parse_conversation_segments(conversation)
            if not segments:
                logger.error("Failed to parse conversation segments")
                raise ValueError("No valid segments generated")
            
            logger.info(f"Parsed {len(segments)} conversation segments")
            audio_segments = []
            
            for i, segment in enumerate(segments):
                logger.info(f"Processing segment {i+1}/{len(segments)}")
                audio_data = self.generate_audio_segment(
                    segment['text'],
                    segment['speaker']
                )
                audio_segments.append(audio_data)

            output_path = self.combine_audio_segments(
                audio_segments,
                output_filename
            )
            
            if output_path:
                logger.info(f"Podcast generated: {output_path}")
                return output_path
            else:
                logger.error("Failed to generate podcast audio")
                raise RuntimeError("Failed to generate podcast audio")
                
        except Exception as e:
            logger.error(f"Error in run_workflow: {str(e)}", exc_info=True)
            raise

    def run(self, conversation: str, output_path: str) -> str:
        """Run the audio processing workflow: parse, generate, and combine segments."""
        logger.debug(f"Starting audio utils workflow for conversation: {conversation[:100]}...")
        segments = self.parse_conversation_segments(conversation)
        if not segments:
            logger.error("Failed to parse conversation segments")
            return None
        logger.info(f"Parsed {len(segments)} conversation segments")
        audio_segments = []
        for i, segment in enumerate(segments):
            logger.info(f"Processing segment {i+1}/{len(segments)}")
            audio_data = self.generate_audio_segment(
                segment['text'],
                segment['speaker']
            )
            audio_segments.append(audio_data)

        output_path = self.combine_audio_segments(
            audio_segments,
            f"podcast_{uuid4()}.mp3"
        )
        if output_path:
            logger.info(f"Podcast generated: {output_path}")
            return output_path
        else:
            logger.warning("Failed to generate podcast audio.")
            return None