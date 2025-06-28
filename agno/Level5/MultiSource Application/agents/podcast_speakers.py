from agno.agent import Agent
from agno.models.google import Gemini
from textwrap import dedent

# Create the podcast speakers agents
# These agents represent two speakers in a podcast conversation.
def create_speaker_a():
    return Agent(
        name="Speaker A - Tech Expert",
        role="Technology expert and podcast host",
        model=Gemini(),
        instructions=[
            dedent("""
            SPEAKER_A: Limit to 20 words, ask questions or comment on content.
            """)
        ],
        debug_mode=True,
    )

def create_speaker_b():
    return Agent(
        name="Speaker B - Industry Analyst",
        role="Industry analyst and guest expert",
        model=Gemini(),
        instructions=[
            dedent("""
            SPEAKER_B: Limit to 20 words, provide data-driven insights.
            """)
        ],
        debug_mode=True,
    )