import os
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google.gemini import Gemini
from agno.storage.sqlite import SqliteStorage
from agno.playground import Playground, serve_playground_app

# Load environment variables from .env file
load_dotenv()
# Set the Google API key for authentication
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Initialize the Agent with Gemini model and persistent session storage
agent = Agent(
    model=Gemini(),
    name="SessionStorageAgent",
    # Fix the session id to continue the same session across execution cycles
    session_id="fixed_id_for_demo",
    # Use SQLite storage to persist conversation memory
    storage=SqliteStorage(table_name="memory", db_file="tmp/memory.db"),
    # Add previous chat history to the messages sent to the model
    add_history_to_messages=True,
    # Number of historical runs to include for context
    num_history_runs=3,
)

# Create a Playground app instance with the configured agent
app = Playground(agents=[agent]).get_app()

# Start the playground web app if this script is run directly
if __name__ == "__main__":
    serve_playground_app("session-storage:app")