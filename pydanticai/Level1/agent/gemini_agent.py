from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
import google.generativeai as genai
from dotenv import load_dotenv
import os
import logfire


class UserInput(BaseModel):
    query: str

class AgentResponse(BaseModel):
    output: str

class HelloWorldAgent:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in .env file")
        
        with logfire.span("Configuring Gemini AI"):
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
            logfire.info("Gemini model initialized", model="gemini-1.5-flash")

    @logfire.instrument("Processing user query")
    def process_query(self, user_input: UserInput) -> AgentResponse:
        if not user_input.query.strip():
            return AgentResponse(output="Please provide a valid question.")

        try:
            with logfire.span("Generating AI response"):
                response = self.model.generate_content(
                    f"Answer in one clear, accurate sentence: {user_input.query}",
                    generation_config={
                        "max_output_tokens": 50,
                        "temperature": 0.5
                    }
                )
                answer = response.text.strip()
                
                logfire.debug("AI response details", 
                    input_tokens=response.usage_metadata.prompt_token_count,
                    output_tokens=response.usage_metadata.candidates_token_count
                )
                
                if not answer or len(answer) < 10:
                    return AgentResponse(output="I couldn't generate a valid response. Try rephrasing.")
                return AgentResponse(output=answer)

        except Exception as e:
            logfire.error("Error processing query", 
                error=str(e),
                query=user_input.query
            )
            return AgentResponse(output=f"Error: {str(e)}")