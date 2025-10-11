import os
from typing import Annotated, TypedDict
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, END, START

# Read GROQ_API_KEY from environment
groq_api_key = os.environ.get("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY environment variable not set.")

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

# List of available tools
tools = [get_weather, add, subtract]

# -------------------- LLM Setup --------------------

# Initialize the LLM with Groq API key and model
llm = ChatGroq(groq_api_key=groq_api_key, model="openai/gpt-oss-20b")


# -------------------- State Definition --------------------

# Create the agent using the built-in create_react_agent
graph = create_react_agent(llm, tools)
