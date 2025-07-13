import google.generativeai as genai
import json
from typing import List
import logfire
from models import UserInput, AgentResponse

class ConversationalAgent:
    def __init__(self, api_key: str):
        logfire.info("Initializing ConversationalAgent")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        self.conversation_history: List[str] = []
        self.system_prompt = (
            "You are a helpful AI assistant. Use the conversation history to provide context-aware responses. "
            "Keep answers concise (max 50 tokens) and accurate. Temperature=0.5."
        )
        self.json_file = "conversation.json"
        logfire.debug("Agent initialized with Gemini model")

    @logfire.instrument("Processing user input")
    def process_input(self, user_input: str) -> str:
        validated_input = UserInput(question=user_input)
        logfire.debug(f"Validated input: {validated_input.question}")
        
        prompt = f"{self.system_prompt}\n\nConversation History:\n{self._format_history()}\n\nUser: {validated_input.question}"
        
        with logfire.span("Generating AI response"):
            try:
                response = self.model.generate_content(
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
                
                return AgentResponse(
                    response=response_text, 
                    conversation_history=self.conversation_history
                ).response
            except Exception as e:
                logfire.error("Failed to generate response", error=str(e))
                raise Exception(f"Failed to generate response: {str(e)}")

    def _format_history(self) -> str:
        return "\n".join(self.conversation_history[-4:]) 

    @logfire.instrument("Saving conversation to JSON")
    def save_conversation_to_json(self):
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