import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from tavily import TavilyClient

# Load environment variables from .env file
load_dotenv()

# Read GROQ_API_KEY from environment
groq_api_key = os.environ.get("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY environment variable not set.")

# Read TAVILY_API_KEY from environment
tavily_api_key = os.environ.get("TAVILY_API_KEY")
if not tavily_api_key:
    raise ValueError("TAVILY_API_KEY environment variable not set.")

tavily_client = TavilyClient(api_key=tavily_api_key)

# -------------------- Tool Definitions --------------------

@tool
def get_weather(location: str) -> str:
    """Call to get the current weather."""
    print(f"[TOOL CALL] get_weather called with: location={location}")
    if location.lower() in ["sf", "san francisco"]:
        result = "It's 60 degrees and foggy."
    else:
        result = "It's 90 degrees and sunny."
    print("[TOOL RESULT] get_weather returned:", result)
    return result

@tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    print(f"[TOOL CALL] add called with: a={a}, b={b}")
    result = a + b
    print("[TOOL RESULT] add returned: ", result)
    return result

@tool
def subtract(a: int, b: int) -> int:
    """Subtract b from a."""
    print(f"[TOOL CALL] subtract called with: a={a}, b={b}")
    result = a - b
    print("[TOOL RESULT] subtract returned:", result)
    return result

@tool
def web_search(query: str) -> str:
    """Search the web for up-to-date information on a topic."""
    print(f"[TOOL CALL] web_search called with: query={query}")
    response = tavily_client.search(query=query, max_results=3)
    results = response.get("results", [])
    result = "\n".join(
        f"- {r['title']}: {r['content']} ({r['url']})" for r in results
    ) or "No results found."
    print("[TOOL RESULT] web_search returned:", result)
    return result

# List of available tools
tools = [get_weather, add, subtract, web_search]

# -------------------- LLM Setup --------------------

# Initialize the LLM with Groq API key and model
llm = ChatGroq(groq_api_key=groq_api_key, model="openai/gpt-oss-120b")


# -------------------- State Definition --------------------

# Create the agent using the built-in create_react_agent
graph = create_react_agent(llm, tools)

# -------------------- Chat Loop --------------------

if __name__ == "__main__":
    print("You can chat with the LLM. It will decide when to use tools (weather, add, subtract, web_search). Type 'exit' to quit.")
    conversation = []
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Exiting chat.")
            break
        # Add user message to conversation
        conversation.append(HumanMessage(content=user_input))
        state = {"messages": conversation}
        # Invoke the graph with the current state
        result = graph.invoke(state)
        # Update conversation with new messages
        conversation = result["messages"]
        print("AI:", conversation[-1].content)
