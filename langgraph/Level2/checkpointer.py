from typing import TypedDict, List
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, END
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Define the agent state structure
class AgentState(TypedDict):
    messages: List[BaseMessage]

# Initialize the LLM with the Groq API key and model
llm = ChatGroq(groq_api_key=GROQ_API_KEY, model="llama-3.3-70b-versatile")

# Node function for the LLM: takes state, appends LLM response to messages
def llm_node(state: AgentState) -> AgentState:
    response = llm.invoke(state["messages"])
    return {"messages": state["messages"] + [response]}

# Set up in-memory checkpointing
checkpointer = InMemorySaver()

# Build the state graph
graph = StateGraph(AgentState)
graph.add_node("llm_node", llm_node)
graph.set_entry_point("llm_node")
graph.add_edge("llm_node", END)

# Compile the app with checkpointing
app = graph.compile(checkpointer=checkpointer)

# Unique thread/session ID for checkpointing
thread_id = "user-session-001"
config = {
    "configurable": {
        "thread_id": thread_id
    }
}

print("You can start chatting with the memory AI bot using checkpointer. Type 'exit' or 'quit' to end the conversation.")

while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit"]:
        print("Exiting the chat.")
        break

    # Retrieve previous state from checkpointer
    previous_state = app.get_state(config)
    if previous_state and "messages" in previous_state.values:
        conversation_history = previous_state.values["messages"]
    else:
        conversation_history = []

    # Add the new user message to the conversation history
    conversation_history.append(HumanMessage(content=user_input))
    input_state = {"messages": conversation_history}

    # Invoke the app and get the AI's response
    result = app.invoke(input_state, config=config)
    ai_message = result["messages"][-1]
    print("AI:", ai_message.content)
