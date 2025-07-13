import os
import sys
from dotenv import load_dotenv
import logfire

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agent import ConversationalAgent
from models import UserInput, AgentResponse

def setup_logfire():
    logfire.configure()
    logfire.info("Logfire configured")

def main():
    load_dotenv()
    setup_logfire()
    
    api_key = os.getenv("GOOGLE_API_KEY")
    logfire_token = os.getenv("LOGFIRE_TOKEN")
    
    if not api_key:
        logfire.error("GOOGLE_API_KEY not found in .env")
        print("Error: GOOGLE_API_KEY not found in .env")
        return

    agent = ConversationalAgent(api_key)
    print("Hello World Agent (type 'quit' to exit)")

    while True:
        user_input = input("\nYour question: ")
        if user_input.lower() == "quit":
            print("Goodbye!")
            agent.save_conversation_to_json() 
            break
        try:
            with logfire.span("Processing user query"):
                response = agent.process_input(user_input)
                print(f"Response: {response}")
                agent.save_conversation_to_json() 
        except Exception as e:
            logfire.error("Error in processing", error=str(e))
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()