from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools import tool
from textwrap import dedent
from utils.audio_utils import AudioUtilsWorkflow
from teams.podcast_team import create_podcast_team
import json
from agno.utils.log import logger

# Initialize global podcast_team and audio_workflow
# This is necessary to ensure they are created only once and can be reused across invocations
try:
    podcast_team = create_podcast_team()
    logger.debug("Successfully initialized podcast team")
except Exception as e:
    logger.error(f"Failed to initialize podcast team: {str(e)}", exc_info=True)
    raise

try:
    audio_workflow = AudioUtilsWorkflow(
        workflow_id="audio_utils_workflow_podcast",
        monitoring=True,
    )
    logger.debug("Successfully initialized AudioUtilsWorkflow")
except Exception as e:
    logger.error(f"Failed to initialize AudioUtilsWorkflow: {str(e)}", exc_info=True)
    raise

# Define the tools for the podcast agent
@tool(show_result=True)
def invoke_podcast_team(topic: str) -> str:
    """Generate a 100-word podcast conversation for the given topic.
    Args:
        topic (str): The topic for the podcast (e.g., 'podcast on https://example.com').
    Returns:
        str: Conversation text with SPEAKER_A and SPEAKER_B labels.
    """
    logger.debug(f"Invoking podcast team with topic: {topic}")
    try:
        response = podcast_team.run(topic)
        if not hasattr(response, 'content') or not isinstance(response.content, str):
            logger.error(f"Invalid podcast team response: {response}")
            raise ValueError("Podcast team response is not a valid string")
        logger.debug(f"Podcast team response: {response.content[:100]}...")
        return response.content
    except Exception as e:
        logger.error(f"Failed to invoke podcast team: {str(e)}", exc_info=True)
        raise

# This tool invokes the audio workflow to generate an MP3 podcast from a conversation.
@tool(show_result=True, stop_after_tool_call=True)
def invoke_audio_workflow(input_data: dict) -> str:
    """Generate an MP3 podcast from a conversation.
    Args:
        input_data (dict): Dict with 'conversation' (str) and 'output_filename' (str).
    Returns:
        str: Path to the generated MP3 file.
    """
    logger.debug(f"Invoking audio workflow with input: {input_data}")
    if not isinstance(input_data, dict) or 'conversation' not in input_data or 'output_filename' not in input_data:
        logger.error("Invalid input_data: must be a dict with 'conversation' and 'output_filename'")
        raise ValueError("Invalid input_data format")
    try:
        result = audio_workflow.run_workflow(input_data)
        logger.debug(f"Audio workflow result: {result}")
        return result
    except Exception as e:
        logger.error(f"Failed to invoke audio workflow: {str(e)}", exc_info=True)
        raise

# Create the podcast agent
# This agent is designed to generate a podcast episode based on a user-provided topic.
def podcast_agent():
    """Initialize the podcast agent."""
    return Agent(
        name="Podcast Conversation Agent",
        model=Gemini(),
        instructions=[
            dedent("""
                You are responsible for generating a short podcast based on a user-provided input, which may be a topic string or a JSON object with 'remaining_text' and 'web_urls'.
                Step-by-step (All steps must be followed and executed in order compulsorily):
        
                2. Use `invoke_podcast_team` with the topic to generate a 100-word conversation between two speakers labeled SPEAKER_A and SPEAKER_B. Log the conversation.
                3. Use `invoke_audio_workflow` with a dict containing 'conversation' (the generated conversation) and 'output_filename' ('podcast_episode') to parse the conversation, generate audio segments, and combine them into a final podcast. Log the audio workflow input.
                4. Return the path to the final podcast audio file.
                Log each step for debugging. Handle errors gracefully and log them.
            """)
        ],
        tools=[
            invoke_podcast_team,
            invoke_audio_workflow
        ],
        debug_mode=True,
    )