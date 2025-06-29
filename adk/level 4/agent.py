from dotenv import load_dotenv
import os
import asyncio
import logging
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from vertexai.preview import rag
from google.genai import types
from prompts import return_instructions_root
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from prompts import return_instructions_root

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
APP_NAME = "rag_app"
USER_ID = "1234"
SESSION_ID = "session1234"
MODEL_GEMINI_2_0_FLASH = "gemini-2.0-flash-001"
AGENT_MODEL = MODEL_GEMINI_2_0_FLASH

# Validate environment variables
for var in ["RAG_CORPUS", "GOOGLE_API_KEY"]:
    if not os.getenv(var):
        raise ValueError(f"{var} environment variable not set.")

# Instantiate Vertex AI RAG Retrieval tool
ask_vertex_retrieval = VertexAiRagRetrieval(
    name="retrieve_rag_documentation",
    description="Use this tool to retrieve documentation and reference materials from the RAG corpus.",
    rag_resources=[
        rag.RagResource(
            rag_corpus=os.environ.get("RAG_CORPUS")
        )
    ],
    similarity_top_k=10,
    vector_distance_threshold=0.6,
)

# Define root agent
root_agent = Agent(
    name="ask_rag_agent",
    model=AGENT_MODEL,
    description="Agent to retrieve and answer queries using Vertex AI RAG corpus.",
    instruction=return_instructions_root(),
    tools=[ask_vertex_retrieval]
)

# Set up session and runner
session_service = InMemorySessionService()
session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)

runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service
)

# Async agent interaction function
async def call_rag_agent(user_input: str) -> str:
    """Sends a query to the RAG agent and returns the response.
    Uses the same session ID to maintain conversation history."""
    logger.info(f"Processing query: {user_input}")
    print(f"\n>>> You: {user_input}")
    user_content = types.Content(role="user", parts=[types.Part(text=user_input)])
    final_response = "No response received."

    try:
        async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=user_content):
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text
                logger.info("Final response generated successfully")
        print(f"<<< Agent: {final_response}")
        return final_response
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        print(f"Error: {str(e)}")
        return f"Error processing query: {str(e)}. Please verify your API keys and try again."

# Interactive loop
async def main():
    print("Vertex AI RAG Agent is running. Type 'exit' to quit.")
    print("Ask a question to retrieve documentation from the RAG corpus!")
    print("\n--- Example conversation: ---")
    print("You could ask: 'What is the latest documentation on Vertex AI RAG?'")
    print("Then follow up with: 'Can you provide more details on RAG corpus setup?'")
    print("--- End example ---\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            logger.info("Exiting program")
            print("Goodbye!")
            break
        if not user_input.strip():
            print("Error: Query cannot be empty.")
            logger.warning("Empty query entered")
            continue
        await call_rag_agent(user_input)

if __name__ == "__main__":
    # Run interactive mode
    asyncio.run(main())