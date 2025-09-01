from langgraph.graph import StateGraph, START, END 
from typing import TypedDict 

# --- Subgraph State --- 
class State(TypedDict):    
    sample: str 
    
# --- Subgraph Node --- 
def subgraph_node_1(state: State):    
    return {"sample": "hi! " + state["sample"]} 

# --- Build Subgraph --- 
subgraph_builder = StateGraph(State) 
subgraph_builder.add_node("subgraph_node_1", subgraph_node_1) 
subgraph_builder.add_edge(START,"subgraph_node_1") 

# Optional if only one node 
subgraph = subgraph_builder.compile() 

# --- Build Parent Graph --- 
parent_builder = StateGraph(State) 
parent_builder.add_node("node_1", subgraph_node_1) 
parent_builder.add_edge(START, "node_1") 
graph = parent_builder.compile() 

# --- Run the Parent Graph --- 
if __name__ == "__main__":    
    result = graph.invoke({"sample": "LangGraph"})    
    print("Final Output:", result)