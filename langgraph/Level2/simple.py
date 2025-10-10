"""
Level 2: Conversational Memory Agent with Groq LLM
An agent that maintains conversation history and context.
"""

import os
from langgraph.graph import StateGraph, END, MessagesState
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage

# Read GROQ_API_KEY from environment
groq_api_key = os.environ.get("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY environment variable not set.")


# Define state with message history
class State(MessagesState):
    pass

# Initialize Groq LLM
llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0.7,
    groq_api_key=groq_api_key
)

# Define agent node with memory
def conversational_agent(state: State):
    """Agent that uses full conversation history"""
    # Pass all messages (conversation history) to LLM
    response = llm.invoke(state["messages"])
    return {"messages": [AIMessage(content=response.content)]}

# Build the graph
def create_memory_graph():
    workflow = StateGraph(State)
    
    # Add node
    workflow.add_node("agent", conversational_agent)
    
    # Set entry point
    workflow.set_entry_point("agent")
    
    # Add edge to end
    workflow.add_edge("agent", END)
    
    return workflow.compile()

# Example usage
if __name__ == "__main__":
    graph = create_memory_graph()
    conversation_state = {"messages": []}

    print("Conversational Memory Agent (type 'exit' to quit)\n" + "="*50)
    while True:
        user_input = input("You: ")
        if user_input.strip().lower() == "exit":
            print("Exiting conversation.")
            break

        conversation_state = graph.invoke({
            "messages": conversation_state["messages"] + [HumanMessage(content=user_input)]
        })

        ai_response = conversation_state["messages"][-1].content
        print("AI:", ai_response)
        print("\n" + "="*50 + "\n")
