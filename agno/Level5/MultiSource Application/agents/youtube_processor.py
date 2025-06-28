from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.youtube import YouTubeTools

# Create the YouTube Processing Agent
# This agent is designed to process YouTube video content, specifically to retrieve captions or transcripts.
def create_youtube_agent():
    return Agent(
        name="YouTube Processor",
        model=Gemini(),
        tools=[YouTubeTools(get_video_captions=True)],
        instructions=[
            "Get YouTube video captions for the provided URL.",
            "Summarize or answer questions based on the transcript or captions(max 1500 characters).",
            "If no transcript, return: 'No transcript available for {url}.'"
        ],
        debug_mode=True,
    )