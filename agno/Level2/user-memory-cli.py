import os
import time
from dotenv import load_dotenv
from agno.agent import Agent
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
from agno.storage.sqlite import SqliteStorage
from agno.models.google.gemini import Gemini
from rich.pretty import pprint

# Load environment variables from .env file
load_dotenv()
# Set the Google API key for authentication
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Set up user-specific memory database for storing user memories
memory_db = SqliteMemoryDb(table_name="user-memory", db_file="tmp/user-memory.db")
memory = Memory(db=memory_db, model=Gemini())

# Set up persistent storage for agent conversation memory
storage = SqliteStorage(table_name="memory", db_file="tmp/memory.db", auto_upgrade_schema=True)

# Define a user ID for associating user-specific memory
user_id = "default_user"

# Initialize the Agent with advanced memory and storage settings
agent = Agent(
    model=Gemini(),
    name="UserMemoryAgent",
    memory=memory,                        # Attach user memory
    storage=storage,                      # Attach persistent storage
    user_id=user_id,                      # Associate with a user
    enable_agentic_memory=True,           # Enable agent's own memory
    enable_user_memories=True,            # Enable user-specific memories
    add_history_to_messages=True,         # Add chat history to model input
    stream=True,                          # Enable streaming responses
    num_history_runs=3,                   # Number of historical runs for context
    markdown=True,                        # Format output as Markdown
    stream_intermediate_steps=True,        # Stream intermediate reasoning steps
    monitoring=True,                      # Enable monitoring for debugging
)

# Helper function to ask the agent a question and wait before the next prompt
def safe_ask(prompt, delay=7):
    agent.print_response(prompt)
    time.sleep(delay)

# Ask questions with throttling to avoid rate limits and allow memory updates
safe_ask("Hello iam sanika")
safe_ask("IAm interested in learning about AI and machine learning")
safe_ask("Give me good career options based on my interests")
safe_ask("Delete all data of mine")
safe_ask("What is my name?")