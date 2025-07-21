import os
import asyncio
from dotenv import load_dotenv
import logfire
from pydantic import BaseModel, Field
from typing import List
from pydantic_ai.agent import Agent
from pydantic_ai.common_tools.tavily import tavily_search_tool

# Load environment variables
load_dotenv()

# Logfire configuration
logfire.configure(token=os.getenv("LOGFIRE_TOKEN"))

# Retrieve API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Validate API keys
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set in .env")
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY not set in .env")

# Define output structure
class Answer(BaseModel):
    answer: str = Field(..., description="The comprehensive answer")
    sources: List[str] = Field(default_factory=list, description="List of source URLs")

# System prompt
SYSTEM_PROMPT = """
You are an AI assistant that provides accurate, up-to-date, and concise answers. 
Use the tavily_search_tool to fetch current information for any question requiring recent data.
Synthesize search results into a clear, coherent answer that directly addresses the user's question, avoiding lists of search results.
Include source URLs at the end of the answer, formatted as a numbered list.
If the search doesn't provide enough information, state that clearly.
"""

# Create agent
agent = Agent(
    model="openai:gpt-4o",
    system_prompt=SYSTEM_PROMPT,
    tools=[tavily_search_tool(TAVILY_API_KEY)],
    output_type=Answer,
)

async def get_answer(question: str) -> Answer:
    with logfire.span("Processing question", question=question):
        try:
            result = await agent.run(question)
            logfire.info(
                "Agent response generated",
                answer_length=len(result.output.answer),
                sources_count=len(result.output.sources)
            )
            return result.output
        except Exception as e:
            logfire.error("Agent processing failed", error=str(e))
            return Answer(answer=f"Sorry, I couldn't process your request due to an error: {str(e)}", sources=[])

async def main():
    print("AI Assistant (type 'quit' or 'exit' to end)")
    print("="*50)
    
    while True:
        question = input("\nYour question: ").strip()
        if question.lower() in ('quit', 'exit'):
            break
            
        with logfire.span("User session", question=question):
            print("\nThinking...")
            answer = await get_answer(question)
            
            print("\n" + "="*50)
            print("ANSWER:")
            print(answer.answer)
            
            if answer.sources:
                print("\nSOURCES:")
                for i, src in enumerate(answer.sources, 1):
                    print(f"{i}. {src}")
            print("="*50)

    print("\nSession ended. View your traces at:")
    print("https://logfire-eu.pydantic.dev/triptytiwari07/pydantic")

if __name__ == "__main__":
    asyncio.run(main())