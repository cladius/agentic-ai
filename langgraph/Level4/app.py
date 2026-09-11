"""
Simple LangGraph RAG agent for a resume.

Same behavior as app.py (the LLM decides on its own when to search the resume,
and can search multiple times before answering), but written as plain functions
instead of a class, to make the LangGraph pieces easier to follow:

START -> "agent" -> (needs to search? -> "tools" -> back to "agent") -> END

- "agent" node: asks the LLM to respond, given the conversation so far.
- "tools" node: if the LLM asked to use the search tool, run it and return the result.
- The loop keeps going until the LLM answers without asking for another search.
"""

import os
from dotenv import find_dotenv, load_dotenv
from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import SentenceTransformersTokenTextSplitter
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
from langchain_core.messages import AnyMessage

# 1. Load GROQ_API_KEY from .env
load_dotenv(find_dotenv())

# 2. Set up the LLM
llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)

# 3. Load the resume PDF and split it into small text chunks
RESUME_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "pydantic", "Level4", "resume.pdf")
pages = PyPDFLoader(RESUME_PATH).load()

splitter = SentenceTransformersTokenTextSplitter(
model_name="sentence-transformers/all-distilroberta-v1",
chunk_overlap=30,
)
chunks = splitter.split_documents(pages)

# 4. Store the chunks as embeddings in a local ChromaDB collection
client = chromadb.PersistentClient(path="./resumedb_simple")
embedding_fn = SentenceTransformerEmbeddingFunction(model_name="all-distilroberta-v1")
collection = client.get_or_create_collection(name="resume", embedding_function=embedding_fn)

if collection.count() == 0:
collection.add(
documents=[chunk.page_content for chunk in chunks],
ids=[f"chunk-{i}" for i in range(len(chunks))],
)


# 5. The one tool the agent is allowed to call
@tool
def search_resume(query: str) -> str:
"""Search the resume and return the most relevant excerpts for the query."""
results = collection.query(query_texts=[query], n_results=2)
return "\n\n".join(results["documents"][0])


tools_by_name = {search_resume.name: search_resume}
llm_with_tools = llm.bind_tools([search_resume])

SYSTEM_PROMPT = (
"You are a helpful assistant. Use the search_resume tool to look up "
"information before answering questions about the resume. You may call "
"it more than once if you need to look up different things."
)


# 6. LangGraph state: just a running list of messages
class AgentState(TypedDict):
messages: Annotated[list[AnyMessage], operator.add]


# 7. Node: ask the LLM what to do next (answer, or call the tool)
def call_agent(state: AgentState):
messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
response = llm_with_tools.invoke(messages)
return {"messages": [response]}


# 8. Node: run whatever tool call(s) the LLM asked for
def call_tools(state: AgentState):
last_message = state["messages"][-1]
results = []
for tool_call in last_message.tool_calls:
tool_fn = tools_by_name[tool_call["name"]]
output = tool_fn.invoke(tool_call["args"])
results.append(ToolMessage(content=str(output), tool_call_id=tool_call["id"]))
return {"messages": results}


# 9. Routing: after the agent responds, did it ask for a tool or is it done?
def agent_wants_tool(state: AgentState) -> bool:
return len(state["messages"][-1].tool_calls) > 0


# 10. Wire the graph together
graph = StateGraph(AgentState)
graph.add_node("agent", call_agent)
graph.add_node("tools", call_tools)
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", agent_wants_tool, {True: "tools", False: END})
graph.add_edge("tools", "agent")
app = graph.compile()


# 11. Simple chat loop
if __name__ == "__main__":
while True:
question = input("You: ")
if question.lower() in ["exit", "quit"]:
print("Exiting the chat.")
break
result = app.invoke({"messages": [HumanMessage(content=question)]})
print("AI:", result["messages"][-1].content)
