from typing import TypedDict, List
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph
import os
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class AgentState(TypedDict):
    messages: List[BaseMessage]

llm = ChatGroq(groq_api_key=GROQ_API_KEY, model="llama-3.3-70b-versatile")

def llm_node(state: AgentState) -> AgentState:
    response = llm.invoke(state["messages"])
    return {"messages": state["messages"] + [response]}

graph = StateGraph(AgentState)
graph.add_node("llm_node", llm_node)
graph.set_entry_point("llm_node")
app = graph.compile()

print("You can start chatting with the memory AI bot. Type 'exit' or 'quit' to end the conversation.")

# Initialize conversation history
conversation_history = []

while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit"]:
        print("Exiting the chat.")
        break

    # Add user message to history
    conversation_history.append(HumanMessage(content=user_input))
    input_state = {"messages": conversation_history}
    result = app.invoke(input_state)
    ai_message = result["messages"][-1]
    print("AI:", ai_message.content)
    # Add AI message to history
    conversation_history.append(ai_message)
