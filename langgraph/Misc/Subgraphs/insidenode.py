from typing_extensions import TypedDict 
from langgraph.graph.state import StateGraph, START 
class SubgraphState(TypedDict):    
    test: str 
    
# Subgraph 
def subgraph_node_1(state: SubgraphState):    
    return {"test": "hi! " + state["test"]} 

subgraph_builder = StateGraph(SubgraphState) 
subgraph_builder.add_node(subgraph_node_1) 
subgraph_builder.add_edge(START, "subgraph_node_1") 
subgraph = subgraph_builder.compile() 

# Parent graph 
class State(TypedDict):    
    sample: str 
    
def call_subgraph(state: State):    
    subgraph_output = subgraph.invoke({"test": state["sample"]})    
    return {"sample": subgraph_output["test"]} 

builder = StateGraph(State) 
builder.add_node("node_1", call_subgraph) 
builder.add_edge(START, "node_1") 
graph = builder.compile() 

# --- Run the Graph --- 
if __name__ == "__main__":    
    result = graph.invoke({"sample": "LangGraph"})    
    print("Final Output:", result)       