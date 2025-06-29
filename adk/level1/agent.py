from dotenv import load_dotenv
import os
import asyncio
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types

# Load environment variables
load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file")

# --- Constants ---
APP_NAME = "programming_concepts_app"
USER_ID = "test_user_123"
MODEL_GEMINI_2_0_FLASH = "gemini-2.0-flash"
AGENT_MODEL = MODEL_GEMINI_2_0_FLASH

# --- Define the Programming Concepts Explainer Agent ---
root_agent = Agent(
    name="programming_concepts_agent",
    model=AGENT_MODEL,
    description="Provides clear explanations of programming concepts for beginners.",
    instruction=(
        "You are a knowledgeable assistant that explains programming concepts clearly and concisely, tailored for beginners. "
        "Answer questions about any programming topic, such as Object-Oriented Programming (OOPS), functions, variables, loops, "
        "data structures, algorithms, or other concepts. "
        "For example, if asked 'What is a function?', explain what a function is with a simple example. "
        "If asked 'What is OOPS?', provide a brief overview of OOPS principles (encapsulation, inheritance, polymorphism, abstraction). "
        "For complex topics like data structures or algorithms, include a beginner-friendly example. "
        "For unrelated questions, politely redirect the user to ask about programming concepts. "
        "Do not use any tools; rely on your knowledge."
    ),
    tools=[]
)

# --- Set up Runner and Session Service ---
session_service = InMemorySessionService()


# --- Agent Interaction Logic ---
async def call_concepts_explainer_agent(user_input: str) -> str:
    """Sends a query to the programming concepts explainer agent and returns the response."""
    print(f"\n>>> You: {user_input}")

    # Create a new session for each interaction to avoid maintaining conversation history
    session_id = f"stateless_session_{os.urandom(4).hex()}"
    session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=session_id)

    # Create a new runner for each interaction
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service
    )

    user_content = types.Content(role="user", parts=[types.Part(text=user_input)])
    final_response = "No response received."

    async for event in runner.run_async(user_id=USER_ID, session_id=session_id, new_message=user_content):
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    print(f"<<< Agent: {final_response}")

    # Clean up the session after each interaction
    session_service.delete_session(app_name=APP_NAME, user_id=USER_ID, session_id=session_id)

    return final_response


# --- Interactive Loop ---
async def main():
    print("Programming Concepts Explainer Agent is running. Type 'exit' to quit.")
    print("Ask about programming concepts, e.g., 'What is a function?' or 'What is OOPS?'")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        await call_concepts_explainer_agent(user_input)


if __name__ == "__main__":
    asyncio.run(main())