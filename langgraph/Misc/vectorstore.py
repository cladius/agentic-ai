from typing import TypedDict, List 
from langchain_astradb import AstraDBVectorStore 
from langchain_huggingface import HuggingFaceEmbeddings 
from langchain_groq import ChatGroq 
from langgraph.graph import StateGraph, END 
import os
from dotenv import load_dotenv
load_dotenv()

# Your Groq API key (keep this secure in production)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ----- Step 1: Define state ----- 
class MemoryState(TypedDict):    
    input: str    
    retrieved_memory: List[str]    
    llm_response: str 
    
# ----- Step 2: Embedding Model ----- 
embedding_model = HuggingFaceEmbeddings(    
    model_name="sentence-transformers/all-MiniLM-L6-v2" ) 

# ----- Step 3: Astra DB Config ----- 
ASTRA_DB_APPLICATION_TOKEN = os.getenv("ASTRA_DB_TOKEN")
ASTRA_DB_API_ENDPOINT = os.getenv("ASTRA_DB_ENDPOINT")
ASTRA_DB_COLLECTION = os.getenv("ASTRA_DB_COLLECTION")

vector_store = AstraDBVectorStore(collection_name=ASTRA_DB_COLLECTION,    
                embedding=embedding_model,api_endpoint=ASTRA_DB_API_ENDPOINT,
                token=ASTRA_DB_APPLICATION_TOKEN,) 

retriever = vector_store.as_retriever() 

# ----- Step 4: Initialize LLM ----- 
llm=ChatGroq(groq_api_key=GROQ_API_KEY,model="llama-3.3-70b-versatile") 

# ----- Step 5: Memory Node with LLM ----- 
def memory_node(state: MemoryState) -> MemoryState:    
    user_input = state["input"]    
    # Store input in AstraDB    
    vector_store.add_texts([user_input])    
    # Retrieve relevant memory    
    relevant_docs = retriever.get_relevant_documents(user_input)   
    retrieved_memory = [doc.page_content for doc in relevant_docs]    
    
    # Build context for LLM    
    context = "\n".join(retrieved_memory)    
    prompt = f"You are a helpful assistant. Use the context below to answer the user's question.\n\nContext:\n{context}\n\nQuestion:\n{user_input}"    
    
    # Get LLM response    
    llm_response = llm.invoke(prompt)    
    return { "input": user_input,"retrieved_memory": retrieved_memory,
            "llm_response": llm_response.content} 

# ----- Step 6: Build LangGraph ----- 
def build_memory_graph():    
    builder = StateGraph(MemoryState)    
    builder.add_node("memory_node", memory_node)    
    builder.set_entry_point("memory_node")    
    builder.add_edge("memory_node", END)    
    return builder.compile() 

graph = build_memory_graph() 

# ----- Step 7: Run Chat Loop ----- 
print("Chat with memory + LLM. Type 'exit' to quit.") 
print("-" * 50) 
while True:
    user_input = input("You: ")    
    if user_input.strip().lower() in ["exit", "quit"]:        
        print("Exiting chat.")        
        break    
    output = graph.invoke({"input": user_input})    
    print("\nRetrieved Memory:")    
    for i, mem in enumerate(output["retrieved_memory"]):        
        print(f"{i + 1}. {mem}")    
        print("\nAssistant:")    
        print(output["llm_response"])    
        print("-" * 50)  
