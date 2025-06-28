from agno.agent import Agent
from agno.models.google import Gemini

# Create the Webpage Processing Agent
# This agent is designed to process webpage content, summarize it, or answer questions.
def create_web_agent():
    return Agent(
        name="Webpage Processor",
        model=Gemini(),
        instructions=[
            "Process webpage content, summarize or answer questions (max 1500 characters).",
            "keep the min length of the content to 300 characters.",
            "If the webpage cannot be accessed or content cannot be extracted, return: 'Failed to extract meaningful content from the webpage.'",
            "If error, return: 'Failed to process webpage content: {content}'."
        ],
        debug_mode=True,
    )