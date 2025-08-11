from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
import google.generativeai as genai
from dotenv import load_dotenv
import os
import logfire


class UserInput(BaseModel):
    """Schema for user input."""
    query: str


class AgentResponse(BaseModel):
    """Schema for agent response."""
    answer: str


# System prompt for the agent
SYSTEM_PROMPT = """
You are a helpful AI assistant powered by Google Gemini, designed to provide clear and accurate answers.
Respond to user queries in a concise and informative manner, ensuring responses are relevant and useful.
If the query is unclear or invalid, politely request clarification.
"""


class GeminiAgent(Agent[None, str]):
    """A basic AI agent powered by Google Gemini LLM with a system prompt."""
    
    def __init__(self):
        """
        Initialize the GeminiAgent with Google Gemini configuration and logging.
        
        Loads environment variables, configures the Gemini API, and sets up the model.
        Raises ValueError if the API key is missing.
        """
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in .env file")
        
        with logfire.span("Configuring Gemini AI"):
            genai.configure(api_key=api_key)
            self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")
            logfire.info("Gemini model initialized", model="gemini-1.5-flash")
            
        # Initialize the parent Agent class with required arguments
        super().__init__(
            model="gemini-1.5-flash",  # Use model name directly
            deps_type=None,
            output_type=str,
            system_prompt=SYSTEM_PROMPT
        )

    def process(self, input_data: UserInput, context: RunContext) -> AgentResponse:
        """
        Process a user query with the system prompt and generate a response using the Gemini LLM.
        
        Args:
            input_data (UserInput): The user's query input.
            context (RunContext): The runtime context for the agent.
        
        Returns:
            AgentResponse: The generated response or an error message.
        """
        if not input_data.query.strip():
            return AgentResponse(answer="Please provide a valid question.")

        try:
            with logfire.span("Generating AI response"):
                # Combine system prompt with user query
                prompt = f"{self.system_prompt}\n\nUser Query: {input_data.query}"
                response = self.gemini_model.generate_content(
                    prompt,
                    generation_config={
                        "max_output_tokens": 100,
                        "temperature": 0.5
                    }
                )
                answer = response.text.strip()
                
                logfire.debug("AI response details", 
                    input_tokens=response.usage_metadata.prompt_token_count,
                    output_tokens=response.usage_metadata.candidates_token_count
                )
                
                if not answer or len(answer) < 10:
                    return AgentResponse(answer="I couldn't generate a valid response. Try rephrasing.")
                return AgentResponse(answer=answer)

        except Exception as e:
            logfire.error("Error processing query", 
                error=str(e),
                query=input_data.query
            )
            return AgentResponse(answer=f"Error: {str(e)}")


def main():
    """
    Run the CLI interface for the GeminiAgent.
    
    Initializes the agent, configures Logfire, and handles user input in a loop until 'quit' is entered.
    """
    try:
        # Suppress LogfireNotConfiguredWarning
        os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'
        # Configure Logfire
        logfire.configure(
            token=os.getenv('LOGFIRE_TOKEN', ''),
            send_to_logfire=True
        )
        with logfire.span("Starting CLI agent"):
            agent = GeminiAgent()
            print("Gemini AI Agent (type 'quit' to exit)")
            print("="*50)
            
            while True:
                try:
                    query = input("\nYour question: ").strip()
                    if query.lower() in ('quit', 'exit'):
                        break

                    with logfire.span("Processing CLI query"):
                        print("\nThinking...")
                        # Initialize RunContext with compatible arguments
                        context = RunContext(
                            deps=None,
                            model="gemini-1.5-flash",
                            usage={},
                            prompt=SYSTEM_PROMPT
                        )
                        response = agent.process(UserInput(query=query), context)
                        print("\n" + "="*50)
                        print("ANSWER:")
                        print(response.answer)
                        print("="*50)

                except KeyboardInterrupt:
                    logfire.info("CLI session ended by user")
                    print("\nGoodbye!")
                    break

    except ValueError as e:
        logfire.error("Agent initialization failed", error=str(e))
        print(f"Error: {e}")

    print("\nSession ended. View your traces at:")
    print("https://logfire-eu.pydantic.dev/triptytiwari07/pydantic")


if __name__ == "__main__":
    main()