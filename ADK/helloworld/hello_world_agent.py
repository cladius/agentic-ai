from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool
from google.genai import types


AGENT_MODEL = "ollama/gemma3"

def greet_user(query: str) -> dict:
    """Responds with 'Hello, World!' if the user greets."""
    if "hello" in query.lower() or "hi" in query.lower():
        return {
            "status": "success",
            "message": "Hello, World!"
        }
    else:
        return {
            "status": "error",
            "error_message": f"Sorry, I only respond to greetings like 'Hello' or 'Hi'."
        }

root_agent = Agent(
   name="hello_world",
   model=LiteLlm(model=AGENT_MODEL),
   description="Say Hello World",
   instruction="You are a friendly agent that responds to greetings.",
   tools=[FunctionTool(func=greet_user)], 
)


if __name__ == "__main__":
    user_input = input("You: ")
    response = greet_user(user_input)
    print(f"Agent: {response['message']}")
