import os
import asyncio
import httpx
from dotenv import load_dotenv
import logfire
from pydantic import BaseModel, Field
from typing import List, Optional
from pydantic_ai.agent import Agent
import google.generativeai as genai


class Answer(BaseModel):
    """Schema for the agent's response, including the answer and source URLs."""
    answer: str = Field(..., description="The comprehensive answer to the user's question")
    sources: List[str] = Field(default_factory=list, description="List of source URLs used to generate the answer")


class TavilySearchInput(BaseModel):
    """Schema for Tavily search tool input."""
    query: str = Field(..., description="The search query")
    search_depth: str = Field(default="basic", description="Search depth: 'basic' or 'advanced'")
    include_answer: bool = Field(default=True, description="Whether to include a direct answer")
    include_raw_content: bool = Field(default=False, description="Whether to include raw content")
    time_range: Optional[str] = Field(default=None, description="Time range for search results (e.g., 'day', 'week')")


async def tavily_search_tool(input_data: TavilySearchInput) -> dict:
    """
    Perform a web search using the Tavily API and return results.
    
    Args:
        input_data (TavilySearchInput): The search query and parameters.
    Returns:
        dict: Search results, including answer and source URLs.
    Raises:
        Exception: If the search fails.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY not set in .env")
    
    with logfire.span("Tavily search", query=input_data.query):
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        **input_data.dict(exclude_none=True),
                        "api_key": api_key
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()
                logfire.info("Tavily search completed", results_count=len(result.get('results', [])))
                return result
            except Exception as e:
                logfire.error("Tavily search failed", error=str(e))
                raise


async def get_answer(question: str, agent: Agent, gemini_model) -> Answer:
    """
    Process a user question using the agent and Gemini model, returning a structured answer.
    
    Uses the Tavily search tool to fetch current information and synthesizes results with Gemini.
    Args:
        question (str): The user's query.
        agent (Agent): The configured Pydantic AI agent with Tavily search tool.
        gemini_model: The configured Gemini model instance.
    Returns:
        Answer: The generated answer with source URLs.
    """
    with logfire.span("Processing question", question=question):
        try:
            # Run Tavily search to get context
            search_input = TavilySearchInput(query=question)
            search_results = await tavily_search_tool(search_input)
            
            # Extract answer and sources
            search_answer = search_results.get('answer', '')
            sources = [result['url'] for result in search_results.get('results', [])]
            
            # Combine search results with Gemini for synthesis
            prompt = (
                f"{agent.system_prompt}\n\n"
                f"User Question: {question}\n"
                f"Search Results: {search_answer}\n"
                f"Provide a concise answer (max 100 tokens) based on the search results."
            )
            gemini_response = gemini_model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": 100,
                    "temperature": 0.5,
                }
            )
            answer_text = gemini_response.text.strip()
            
            logfire.info(
                "Agent response generated",
                answer_length=len(answer_text),
                sources_count=len(sources)
            )
            return Answer(answer=answer_text, sources=sources)
        except Exception as e:
            logfire.error("Agent processing failed", error=str(e))
            return Answer(answer=f"Sorry, I couldn't process your request due to an error: {str(e)}", sources=[])


async def main():
    """
    Run the CLI interface for the AI Assistant with web search capabilities.
    
    Initializes the agent and Gemini model, handles user input, and displays answers with sources.
    Exits on 'quit' or Ctrl+C.
    """
    # Load environment variables
    load_dotenv()
    
    # Configure Logfire
    os.environ['LOGFIRE_IGNORE_NO_CONFIG'] = '1'
    logfire.configure(
        token=os.getenv('LOGFIRE_TOKEN', ''),
        send_to_logfire=True
    )
    logfire.info("Logfire configured")
    
    # Validate API keys
    google_api_key = os.getenv("GOOGLE_API_KEY")
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not google_api_key:
        logfire.error("GOOGLE_API_KEY not set in .env")
        print("Error: GOOGLE_API_KEY not set in .env")
        return
    if not tavily_api_key:
        logfire.error("TAVILY_API_KEY not set in .env")
        print("Error: TAVILY_API_KEY not set in .env")
        return
    
    # Configure Gemini model
    genai.configure(api_key=google_api_key)
    gemini_model = genai.GenerativeModel(os.getenv("MODEL", "gemini-1.5-flash"))
    
    # Create agent
    system_prompt = """
    You are an AI assistant that provides accurate, up-to-date, and concise answers. 
    Use the tavily_search_tool to fetch current information for any question requiring recent data.
    Synthesize search results into a clear, coherent answer that directly addresses the user's question, avoiding lists of search results.
    Include source URLs at the end of the answer, formatted as a numbered list.
    If the search doesn't provide enough information, state that clearly.
    """
    agent = Agent(
        model=os.getenv("MODEL", "gemini-1.5-flash"),
        system_prompt=system_prompt,
        tools=[tavily_search_tool],
        output_type=Answer,
    )
    
    print("AI Assistant with Web Search (type 'quit' or 'exit' to end)")
    print("="*50)
    
    while True:
        try:
            question = input("\nYour question: ").strip()
            if question.lower() in ('quit', 'exit'):
                print("\nGoodbye!")
                break
            
            with logfire.span("User session", question=question):
                print("\nThinking...")
                answer = await get_answer(question, agent, gemini_model)
                
                print("\n" + "="*50)
                print("ANSWER:")
                print(answer.answer)
                
                if answer.sources:
                    print("\nSOURCES:")
                    for i, src in enumerate(answer.sources, 1):
                        print(f"{i}. {src}")
                print("="*50)
        
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            logfire.error("Error in processing", error=str(e))
            print(f"Error: {str(e)}")
    
    print("\nSession ended. View your traces at:")
    print("https://logfire-eu.pydantic.dev/triptytiwari07/pydantic")


if __name__ == "__main__":
    asyncio.run(main())