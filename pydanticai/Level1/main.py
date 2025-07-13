from agent.gemini_agent import HelloWorldAgent, UserInput, AgentResponse
import logfire
from dotenv import load_dotenv
import os

load_dotenv()

# Configure Logfire for CLI
logfire.configure(
    token=os.getenv('LOGFIRE_TOKEN'),
    send_to_logfire=True
)

def main():
    try:
        with logfire.span("Starting CLI agent"):
            agent = HelloWorldAgent()
            print("Hello World Agent (type 'quit' to exit)")
            
            while True:
                try:
                    query = input("\nYour question: ")
                    if query.lower() == 'quit':
                        break

                    with logfire.span("Processing CLI query"):
                        response = agent.process_query(UserInput(query=query))
                        print("Response:", response.output)

                except KeyboardInterrupt:
                    logfire.info("CLI session ended by user")
                    print("\nGoodbye!")
                    break

    except ValueError as e:
        logfire.error("Agent initialization failed", error=str(e))
        print(f"Error: {e}")

if __name__ == "__main__":
    main()