from agno.agent import Agent
from agno.models.google import Gemini
from textwrap import dedent

# Create the Text Processing Agent
# This agent is designed to process plain text input, summarize it, or answer questions.    
# It also routes specific requests to the appropriate agents for podcasts and mindmaps.
def create_text_agent():
    return Agent(
        name="Text Processor",
        model=Gemini(),
        instructions=[
            dedent("""
            Process plain text input. Answer the questions (max 1500 characters).
            If podcast request, return: 'Podcast request should be handled by Podcast Conversation Team.' and route to podcast_agent.
            If mindmap request, return: 'Mindmap request should be handled by Mindmap Agent.' and route to mindmap_agent.
            """)
        ],
        debug_mode=True,
    )
