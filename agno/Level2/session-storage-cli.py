import os
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google.gemini import Gemini
from agno.storage.sqlite import SqliteStorage
from rich.pretty import pprint

# Load environment variables from .env file
load_dotenv()
# Set the Google API key for authentication
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Initialize the Agent with Gemini model and persistent session storage
agent = Agent(
    model=Gemini(),
    name="Session Storage Agent",
    # Fix the session id to continue the same session across execution cycles
    session_id="fixed_id_for_demo",
    # Use SQLite storage to persist conversation memory
    storage=SqliteStorage(table_name="agent_sessions", db_file="tmp/data.db"),
    # Add previous chat history to the messages sent to the model
    add_history_to_messages=True,
    # Number of historical runs to include for context
    num_history_runs=3,
    monitoring=True,
    markdown=True,
    stream=True,
    stream_intermediate_steps=True,
)

# Prompt the agent with a question
agent.print_response("What is the capital of France?")
# Ask a follow-up question to test session memory
agent.print_response("What was my last question?")
# Pretty-print the messages currently stored in the agent's session memory
pprint(agent.get_messages_for_session())