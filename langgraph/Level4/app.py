from dotenv import find_dotenv, load_dotenv
from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import SentenceTransformersTokenTextSplitter
import chromadb
from langchain_chroma import Chroma
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from langchain_core.tools import tool,StructuredTool
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage
import os

# Load environment variables from a .env file
load_dotenv(find_dotenv())

# Initialize the language model with specific parameters
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

# Load a PDF file (resume) using LangChain's PyPDFLoader
pdf_loader = PyPDFLoader("C:\\Users\\LENOVO\\Desktop\\Agentic AI\\Langgraph-Rag\\RAG\\Khushboo-Patil-Resume.pdf") # Specify the path to your resume PDF
pages = pdf_loader.load() # Load all pages as document objects

# Split the loaded PDF pages into smaller text chunks for embedding
text_splitter = SentenceTransformersTokenTextSplitter(
    model_name = "sentence-transformers/all-distilroberta-v1", # Model for tokenization
    chunk_overlap = 30, # Overlap between chunks for context
)
split_pages = text_splitter.split_documents(pages) # Split into chunks

# Create a persistent ChromaDB collection and add the split resume chunks as embeddings
persistent_client = chromadb.PersistentClient(path="./resumedb") # Persistent DB location
distil_roberta = SentenceTransformerEmbeddingFunction(model_name="all-distilroberta-v1") # Embedding function
collection = persistent_client.create_collection(
    name="resume",
    metadata={
        "title": "Resume",
        "description": "This store contains embeddings of Resume"
    },
    embedding_function = distil_roberta,
    get_or_create = True
)

# Add documents, ids, and metadata to the collection for retrieval
collection.add(
    documents=[doc.page_content for doc in split_pages],
    ids=[f"Chunk-{idx}" for idx, doc in enumerate(split_pages, start=1)],
    metadatas= [doc.metadata for doc in split_pages]
)

# Define a LangChain tool to retrieve information from the resume collection
@tool
def retriever_tool(query):
    """
    search_resume_file:
    Search and return projects information from the resume file.

    Args:
        query (str): The search query to retrieve relevant information from the resume.

    Returns:
        str: The top 2 relevant chunks of text from the resume.
    """
    results = collection.query(
        query_texts=[query,],
        n_results=2 # Return top 2 relevant chunks
    )

    return "\n\n\n".join(results["documents"][0])

tools = [retriever_tool]

# Define a custom RAG (Retrieval Augmented Generation) agent using LangGraph
class AgentState(TypedDict):
    """
    A typed dictionary to represent the state of the agent.

    Attributes:
        messages (list[AnyMessage]): A list of messages exchanged between the user and the agent.
    """
    messages: Annotated[list[AnyMessage], operator.add]

# RAGAgent class encapsulates the agent logic and graph
class RAGAgent:
    """
    A custom Retrieval-Augmented Generation (RAG) agent that uses LangGraph to manage reasoning steps.

    Attributes:
        model: The language model used for generating responses.
        tools (dict): A dictionary of tools available to the agent.
        system (str): The system prompt for the agent.
        graph: The state graph that defines the agent's reasoning process.
    """

    def __init__(self, model, tools, system="You are a helpful assistant"):
        """
        Initialize the RAGAgent with a language model, tools, and a system prompt.

        Args:
            model: The language model to use.
            tools (list): A list of tools available to the agent.
            system (str): The system prompt for the agent.
        """
        self.system = system
        self.tools = {t.name: t for t in tools}
        self.model = model.bind_tools(tools, tool_choice="auto")

        # Build the state graph for the agent
        graph = StateGraph(AgentState)
        graph.add_node("llm", self.call_llm)
        graph.add_node("retriever", self.take_action)
        graph.add_conditional_edges(
            "llm",
            self.exists_action,
            {True : "retriever", False : END}
        )
        graph.add_edge("retriever", "llm")
        graph.set_entry_point("llm")
        self.graph = graph.compile()

    def exists_action(self, state: AgentState):
        """
        Check if the last message contains tool calls.

        Args:
            state (AgentState): The current state of the agent.

        Returns:
            bool: True if tool calls exist, False otherwise.
        """
        result = state['messages'][-1]
        return len(result.tool_calls) > 0

    def call_llm(self,state: AgentState):
        """
        Call the language model with the current messages and system prompt.

        Args:
            state (AgentState): The current state of the agent.

        Returns:
            dict: The updated state with the language model's response.
        """
        messages = state['messages']
        if self.system:
            messages = [SystemMessage(content=self.system)] + messages
        message = self.model.invoke(messages)
        return {'messages' : [message]}

    def take_action(self, state: AgentState):
        """
        Execute the tool calls and return results as ToolMessages.

        Args:
            state (AgentState): The current state of the agent.

        Returns:
            dict: The updated state with the tool execution results.
        """
        tool_calls = state['messages'][-1].tool_calls
        results = []
        for t in tool_calls:
            if not t['name'] in self.tools:
                print(f"\n Tool: {t} does not exist.")
                result = "Incorrect tool name, Please Retry and select tools from list of available tools."
            else:
                result = self.tools[t['name']].invoke(t['args'])
            results.append(ToolMessage(tool_call_id=t['id'], name=t['name'], content=str(result)))
        return {'messages' : results}

# Define the system prompt for the agent
prompt = """
You are a helpful assistant. Use the retriever tool available to answer questions.
You are allowed to make multiple calls (either together or in sequence).
If you need to look up some information before asking a follow up question, you are allowed to do that!.
"""

# Instantiate the RAGAgent
agent = RAGAgent(llm, tools, system = prompt)

# Main loop for user interaction
while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit"]:
        print("Exiting the chat.")
        break
    messages = [HumanMessage(content=user_input)]
    result = agent.graph.invoke({"messages":messages})
    print(result['messages'][-1].content)