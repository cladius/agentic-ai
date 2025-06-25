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
APP_NAME = "career_advisor_app"
USER_ID = "test_user_123"
SESSION_ID = "conversation_session_abc"
MODEL_GEMINI_2_0_FLASH = "gemini-2.0-flash"
AGENT_MODEL = MODEL_GEMINI_2_0_FLASH

# --- Define the Conversational Career Advisor Agent ---
root_agent = Agent(
    name="career_advisor",
    model=AGENT_MODEL,
    description="A conversational agent that guides users about different career paths and remembers user details.",
    instruction=(
        "You are a knowledgeable assistant that helps users explore career options based on their interests and background. "
        "Pay close attention to personal details that users share, such as their name, educational background, and interests. "
        "Remember these details throughout the conversation to provide personalized advice. "
        "For example, if a user mentions they are interested in compiler design and ML, reference these interests in future responses. "
        "Provide specific career path recommendations, relevant textbooks, learning resources, and potential job roles that align with their stated interests. "
        "Be conversational, personable, and address the user by name when appropriate. "
        "When recommending textbooks or resources, be specific and explain why they're relevant to the user's particular interests."
    ),
    tools=[]
)

# --- Set up Session Management and Runner ---
# Using persistent session to maintain conversation history
session_service = InMemorySessionService()
session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)

runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service
)


# --- Agent Interaction Logic ---
async def call_career_advisor_agent(user_input: str) -> str:
    """Sends a query to the career advisor agent and returns the response.
    Uses the same session ID to maintain conversation history."""
    print(f"\n>>> You: {user_input}")
    user_content = types.Content(role="user", parts=[types.Part(text=user_input)])
    final_response = "No response received."

    # Using the same session ID for all interactions to maintain conversation history
    async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=user_content):
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text

    print(f"<<< Agent: {final_response}")
    return final_response


# --- Interactive Loop ---
async def main():
    print("Career Advisor Agent is running. Type 'exit' to quit.")
    print("Introduce yourself and ask about career options!")

    # Example conversation starter to demonstrate the feature
    print("\n--- Example conversation: ---")
    print(
        "You could tell the agent about yourself and ask What are some good career options?'")
    print("Then follow up with: 'What are some relevant textbooks that align with my interests?'")
    print("--- End example ---\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        await call_career_advisor_agent(user_input)


if __name__ == "__main__":
    asyncio.run(main())