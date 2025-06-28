import os
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google.gemini import Gemini
from rich.pretty import pprint

# Load environment variables from .env file
load_dotenv()
# Set the Google API key for authentication
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Initialize the Agent 
agent = Agent(
    model=Gemini(),
    # Add previous chat history to the messages sent to the model
    add_history_to_messages=True,
    # Number of historical responses to include for context
    num_history_responses=3,
    # Description to guide the agent's behavior
    description="You are a helpful assistant that always responds in a polite, upbeat and positive manner.",
    monitoring=True,
    markdown=True,
    stream_intermediate_steps=True,
)

# Create a conversation by prompting the agent
agent.print_response("Share a 2 sentence horror story", stream=True)

# Print the messages currently stored in the agent's memory
pprint(
    [
        m.model_dump(include={"role", "content"})
        for m in agent.get_messages_for_session()
    ]
)

# Ask a follow-up question to continue the conversation
agent.print_response("What was my first message?", stream=True)

# Print the updated messages in the agent's memory
pprint(
    [
        m.model_dump(include={"role", "content"})
        for m in agent.get_messages_for_session()
    ]
)