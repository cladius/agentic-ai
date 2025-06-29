import logging
from pydub import AudioSegment
import base64
import asyncio
import os

logger = logging.getLogger(__name__)

# --- Audio Processing Utilities ---
class AudioProcessor:
    @staticmethod
    def convert_to_pcm_16khz(audio_file_path: str) -> bytes:
        """
        Converts an audio file to PCM format with a 16kHz sample rate, mono channel, and 16-bit sample width.

        Args:
            audio_file_path (str): Path to the input audio file.

        Returns:
            bytes: PCM audio data.

        The 16kHz sample rate is chosen because it provides a good balance between audio quality and file size,
        making it suitable for speech processing applications. It captures the essential frequencies of human speech
        (typically up to 8kHz, per the Nyquist-Shannon theorem) while keeping computational and storage requirements low.
        Many speech recognition systems, such as Whisper, are optimized for 16kHz audio inputs, ensuring compatibility
        and efficient processing. The mono channel reduces data complexity, and 16-bit sample width ensures sufficient
        dynamic range for clear audio representation.
        """
        try:
            # Load the audio file using pydub
            audio = AudioSegment.from_file(audio_file_path)
            # Set to mono channel to simplify processing and reduce data size
            audio = audio.set_channels(1)
            # Set sample rate to 16kHz for compatibility with speech processing systems
            audio = audio.set_frame_rate(16000)
            # Set sample width to 2 bytes (16-bit) for sufficient audio quality
            audio = audio.set_sample_width(2)
            # Temporary file to store the converted audio
            output_path = "temp_pcm.wav"
            # Export the processed audio as a WAV file
            audio.export(output_path, format="wav")
            # Read the PCM data from the temporary file
            with open(output_path, "rb") as f:
                pcm_data = f.read()
            # Clean up the temporary file
            os.remove(output_path)
            return pcm_data
        except Exception as e:
            logger.error(f"Error processing audio file: {e}")
            raise
    
    @staticmethod
    def audio_to_base64(audio_data: bytes) -> str:
        """
        Converts raw audio data to a base64-encoded string.

        Args:
            audio_data (bytes): Raw PCM audio data.

        Returns:
            str: Base64-encoded string of the audio data.
        """
        return base64.b64encode(audio_data).decode('utf-8')
    
    @staticmethod
    async def process_audio_file_async(file_path: str) -> str:
        """
        Asynchronously processes an audio file to PCM 16kHz and converts it to base64.

        Args:
            file_path (str): Path to the input audio file.

        Returns:
            str: Base64-encoded string of the processed PCM audio data.

        This method runs the synchronous convert_to_pcm_16khz in an executor to avoid blocking
        the event loop, then converts the result to base64.
        """
        loop = asyncio.get_event_loop()
        audio_data = await loop.run_in_executor(None, AudioProcessor.convert_to_pcm_16khz, file_path)
        return AudioProcessor.audio_to_base64(audio_data)