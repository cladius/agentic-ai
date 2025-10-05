from typing import TypedDict, List
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import Runnable
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END

import os


# Read Groq API key from shell environment variable only
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

class AgentState(TypedDict):
    """
    Defines the state passed between nodes in the agent graph.
    """
    messages: List[BaseMessage]

# Initialize the LLM with the Groq API key and model name
llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model="llama-3.3-70b-versatile"
)

def call_model(state: AgentState) -> AgentState:
    """
    Calls the language model with the current messages and appends the response.
    """
    response = llm.invoke(state["messages"])
    state["messages"].append(response)
    return state

# Build the agent graph
builder = StateGraph(AgentState)
builder.add_node("respond", call_model)         # Add a node that calls the model
builder.set_entry_point("respond")              # Set the entry point of the graph
builder.add_edge("respond", END)                # End after the respond node
graph = builder.compile()                       # Compile the graph



# Interactive loop for user input
messages = []
print("Type your question and press Enter. Type 'exit' to quit.")
while True:
    user_message = input("You: ")
    if user_message.strip().lower() == "exit":
        print("Exiting.")
        break
    messages.append(HumanMessage(content=user_message))
    inputs = {"messages": messages.copy()}
    print("Agent:")
    response = graph.invoke(inputs)
    # Print only the latest response
    print(response["messages"][-1].content)
    # Add the agent's response to the message history
    messages.append(response["messages"][-1])
