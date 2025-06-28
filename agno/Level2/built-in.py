import os
from agno.agent import Agent
from agno.models.google.gemini import Gemini
from agno.playground import Playground, serve_playground_app
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set the Google API key for authentication
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Initialize the Agent with Gemini model and memory settings
agent = Agent(
    name="Built-In Memory Agent",
    model=Gemini(),
    # Enable adding previous chat history to the model's messages
    add_history_to_messages=True,
    # Specify how many previous responses to include for context
    num_history_responses=3,
    # Set a description to guide the agent's behavior
    description="You are a helpful assistant that always responds in a polite, upbeat and positive manner.",
)

# Create a Playground app instance with the configured agent
app = Playground(agents=[agent]).get_app()

# Start the playground web app if this script is run directly
if __name__ == "__main__":
    serve_playground_app("built-in:app")