from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
import google.generativeai as genai
from dotenv import load_dotenv
import os
import json
from typing import List
import logfire


class UserInput(BaseModel):
    """Schema for user input."""
    question: str


class AgentResponse(BaseModel):
    """Schema for agent response."""
    response: str
    conversation_history: List[str]


class ConversationalAgent(Agent[None, str]):
    """A conversational AI agent powered by Google Gemini with memory and logging."""
    
    def __init__(self):
        """
        Initialize the ConversationalAgent with Gemini configuration and logging.
        
        Loads environment variables, configures the Gemini API, and sets up conversation history.
        Raises:
            ValueError: If GOOGLE_API_KEY is missing.
        """
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in .env")
        
        with logfire.span("Initializing ConversationalAgent"):
            genai.configure(api_key=api_key)
            self.gemini_model = genai.GenerativeModel(
                os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            )
            self.conversation_history: List[str] = []
            self.system_prompt = (
                "You are a helpful AI assistant. Use the conversation history to provide context-aware responses. "
                "Keep answers concise (max 50 tokens) and accurate. Temperature=0.5."
            )
            self.json_file = os.getenv("CONVERSATION_FILE", "conversation.json")
            logfire.info("Agent initialized", model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
            
        # Initialize the parent Agent class
        super().__init__(
            model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            deps_type=None,
            output_type=str,
            system_prompt=self.system_prompt
        )

    def process(self, input_data: UserInput, context: RunContext) -> AgentResponse:
        """
        Process a user query with conversation history and generate a response using Gemini.
        
        Validates input, appends to history, generates a response, and saves to JSON.
        Args:
            input_data (UserInput): The user's query.
            context (RunContext): The runtime context for the agent.
        Returns:
            AgentResponse: The generated response with conversation history.
        Raises:
            Exception: If response generation fails.
        """
        with logfire.span("Processing user input"):
            validated_input = UserInput(question=input_data.question)
            logfire.debug(f"Validated input: {validated_input.question}")
            
            prompt = f"{self.system_prompt}\n\nConversation History:\n{self._format_history()}\n\nUser: {validated_input.question}"
            
            try:
                response = self.gemini_model.generate_content(
                    prompt,
                    generation_config={
                        "max_output_tokens": 50,
                        "temperature": 0.5,
                    }
                )
                response_text = response.text.strip()
                self.conversation_history.append(f"User: {validated_input.question}")
                self.conversation_history.append(f"AI: {response_text}")
                
                logfire.info("Response generated", 
                            response_length=len(response_text),
                            conversation_length=len(self.conversation_history))
                
                self._save_conversation_to_json()
                return AgentResponse(
                    response=response_text,
                    conversation_history=self.conversation_history
                )
            except Exception as e:
                logfire.error("Failed to generate response", error=str(e))
                raise Exception(f"Failed to generate response: {str(e)}")

    def _format_history(self) -> str:
        """
        Format the last 4 entries of conversation history for inclusion in the prompt.
        
        Returns:
            str: Formatted conversation history as a string.
        """
        return "\n".join(self.conversation_history[-4:])

    def _save_conversation_to_json(self):
        """
        Save the conversation history to a JSON file.
        
        Structures the history as user-response pairs and writes to the specified JSON file.
        """
        with logfire.span("Saving conversation to JSON"):
            exchanges = []
            for i in range(0, len(self.conversation_history), 2):
                if i + 1 < len(self.conversation_history):
                    user_input = self.conversation_history[i].replace("User: ", "")
                    ai_response = self.conversation_history[i + 1].replace("AI: ", "")
                    exchanges.append({"user": user_input, "response": ai_response})
            
            with open(self.json_file, "w") as f:
                json.dump({"conversation": exchanges}, f, indent=2)
            
            logfire.info("Conversation saved", 
                        file_path=self.json_file,
                        exchange_count=len(exchanges))


def setup_logfire():
    """
    Configure Logfire for logging and performance tracing.
    
    Uses LOGFIRE_TOKEN from .env or defaults to empty string.
    Suppresses configuration warnings.
    """
    os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'
    logfire.configure(
        token=os.getenv('LOGFIRE_TOKEN', ''),
        send_to_logfire=True
    )
    logfire.info("Logfire configured")


def main():
    """
    Run the CLI interface for the ConversationalAgent.
    
    Initializes the agent, handles user input, and saves conversation history.
    Exits on 'quit' or Ctrl+C.
    """
    load_dotenv()
    setup_logfire()
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logfire.error("GOOGLE_API_KEY not found in .env")
        print("Error: GOOGLE_API_KEY not found in .env")
        return

    with logfire.span("Starting CLI agent"):
        agent = ConversationalAgent()
        print("Conversational AI Agent (type 'quit' to exit)")
        print("="*50)
        
        while True:
            try:
                user_input = input("\nYour question: ").strip()
                if user_input.lower() in ('quit', 'exit'):
                    print("Goodbye!")
                    agent._save_conversation_to_json()
                    break
                
                with logfire.span("Processing user query"):
                    print("\nThinking...")
                    context = RunContext(
                        deps=None,
                        model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                        usage={},
                        prompt=agent.system_prompt
                    )
                    response = agent.process(UserInput(question=user_input), context)
                    print("\n" + "="*50)
                    print("ANSWER:")
                    print(response.response)
                    print("="*50)
                    
            except Exception as e:
                logfire.error("Error in processing", error=str(e))
                print(f"Error: {str(e)}")
                
        print("\nSession ended. View your traces at:")
        print("https://logfire-eu.pydantic.dev/triptytiwari07/pydantic")


if __name__ == "__main__":
    main()