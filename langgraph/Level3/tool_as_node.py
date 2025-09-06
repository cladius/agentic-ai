import os
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, END, START

# Load environment variables from .env file
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

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
llm = ChatGroq(groq_api_key=GROQ_API_KEY, model="llama-3.3-70b-versatile")
llm_with_tools = llm.bind_tools(tools)

# -------------------- State Definition --------------------

class State(TypedDict):
    messages: Annotated[list, add_messages]

# Create a state graph for the conversation flow
graph_builder = StateGraph(State)

# Node: Chatbot LLM invocation
def chatbot(state: State):
    # Pass conversation messages to the LLM and get the response
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

graph_builder.add_node("chatbot", chatbot)

# Node: Tool execution
tool_node = ToolNode(tools)
graph_builder.add_node("tools", tool_node)

# Conditional edge: If tool is needed, go to tool node
graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)

# After tool execution, return to chatbot
graph_builder.add_edge("tools", "chatbot")
# Start the graph at the chatbot node
graph_builder.add_edge(START, "chatbot")

# Compile the graph
graph = graph_builder.compile()

# -------------------- Chat Loop --------------------

print("You can chat with the LLM. It will decide when to use tools (weather, add, subtract). Type 'exit' to quit.")
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