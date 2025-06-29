from dotenv import load_dotenv
import os
import asyncio
import logging
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.langchain_tool import LangchainTool
from google.genai import types
from langchain_community.tools import TavilySearchResults

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
APP_NAME = "news_app"
USER_ID = "1234"
SESSION_ID = "session1234"
MODEL_GEMINI_1_5_FLASH = "gemini-1.5-flash"  # Valid model
AGENT_MODEL = MODEL_GEMINI_1_5_FLASH

# Validate environment variables
if not os.getenv("TAVILY_API_KEY"):
    raise ValueError("TAVILY_API_KEY environment variable not set.")
if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("GOOGLE_API_KEY environment variable not set.")

# Instantiate Tavily search tool optimized for news
tavily_search = TavilySearchResults(
    max_results=4,
    search_depth="advanced",
    include_answer=True,
    include_raw_content=True,
    include_images=False,  # Images not needed for news summaries
    include_domains=["reuters.com", "nytimes.com", "cbsnews.com", "npr.org", "theguardian.com"]  # Focus on reputable news sources
)

# Wrap with LangchainTool
adk_tavily_tool = LangchainTool(tool=tavily_search)

# Define root agent explicitly
root_agent = Agent(
    name="langchain_tool_agent",
    model=AGENT_MODEL,
    description="Agent to provide the latest news on all aspects using TavilySearch.",
    instruction="""
    You are a news assistant that uses the TavilySearch tool to find the latest information on a wide range of topics, including but not limited to tariffs, politics, economics, social issues, international relations, and other significant developments.
    
    ALWAYS use the TavilySearch tool to fetch recent news articles when answering queries.
    
    When responding:
    1. Use the TavilySearch tool to search for the most recent news articles relevant to the query.
    2. Analyze the search results to extract comprehensive information, including key details such as events, figures (e.g., economic impacts, policy changes, dates), stakeholders (e.g., governments, organizations, companies), and broader implications.
    3. Provide a detailed, well-structured summary of all the latest developments, covering multiple aspects (e.g., political, economic, social, international) as relevant to the query.
    4. Cite sources by mentioning the news outlets (e.g., Reuters, The New York Times) from the search results, including publication dates where available.
    5. If the query is broad (e.g., 'latest news'), cover major developments across key areas such as US and global politics, economic trends, trade policies (including tariffs), social movements, international relations, and significant events, ensuring no major recent development is omitted.
    6. Ensure the response is comprehensive, clear, and organized, with specific details and context for each topic covered.
    
    DO NOT respond that you lack real-time data - you must use the TavilySearch tool.
    """,
    tools=[adk_tavily_tool]
)

# Set up session and runner
session_service = InMemorySessionService()
session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)

runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service
)

# Async agent interaction function
async def call_agent(query: str) -> str:
    """Sends a query to the agent and returns the response."""
    logger.info(f"Processing query: {query}")
    print(f"\n>>> You: {query}")
    user_content = types.Content(role="user", parts=[types.Part(text=query)])
    final_response = "No response received."

    try:
        async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=user_content):
            if event.is_final_response() and event.content and event.content.parts:
                final_response = event.content.parts[0].text
                logger.info("Final response generated successfully")
        print(f"<<< Agent: {final_response}")
        return final_response
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        print(f"Error: {str(e)}")
        return f"Error processing query: {str(e)}. Please verify your API keys and try again."

# Interactive loop
async def main():
    print("News Agent is running. Type 'exit' to quit.")
    print("Ask about the latest news, e.g., 'What is the latest news?'")

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == "exit":
            logger.info("Exiting program")
            print("Goodbye!")
            break
        if not user_input.strip():
            print("Error: Query cannot be empty.")
            logger.warning("Empty query entered")
            continue
        await call_agent(user_input)

# Example usage
if __name__ == "__main__":
    # Run interactive mode to prompt user for input
    asyncio.run(main())
