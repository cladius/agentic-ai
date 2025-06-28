import os
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google.gemini import Gemini

# Load environment variables from .env file
load_dotenv()

# Set the Google API key for authentication
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Initialize the Agent with the Gemini model and desired settings
agent = Agent(
    name="HelloWorld",
    model=Gemini(),
    markdown=True,
    monitoring=True
)

# Prompt the agent to write a report on NVDA, streaming the response with full reasoning and intermediate steps
agent.print_response("Write a report on NVDA", stream=True, show_full_reasoning=True, stream_intermediate_steps=True)