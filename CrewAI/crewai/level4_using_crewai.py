# level4_using_crewai.py  (Ollama-only, no OpenAI)
import os

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

# New, non-deprecated Ollama integrations
from langchain_ollama import OllamaEmbeddings, ChatOllama

from langchain.chains import RetrievalQA

from crewai import Agent, Task, Crew
# from crewai.tools import tool  # use class, not decorator

PDF_PATH = "resume_updated.pdf"          # update to your PDF path
EMBED_MODEL = "nomic-embed-text:latest"  # ollama embedding model
LLM_MODEL = "llama3:latest"             # ollama LLM

def build_retriever(pdf_path: str):
    docs = PyPDFLoader(pdf_path).load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=150,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = splitter.split_documents(docs)

    embeddings = OllamaEmbeddings(model=EMBED_MODEL)  # no API keys needed
    vectordb = FAISS.from_documents(chunks, embeddings)
    return vectordb.as_retriever(search_type="similarity", search_kwargs={"k": 4})

def simple_rag_answer(retriever, question: str) -> str:
    llm = ChatOllama(model=LLM_MODEL, temperature=0)
    qa = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        return_source_documents=False
    )
    # use invoke (run is deprecated)
    out = qa.invoke({"query": question})
    return out if isinstance(out, str) else out.get("result", str(out))

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type

# Optional: schema for validation
class PDFQuery(BaseModel):
    query: str = Field(..., description="Question to answer from the PDF")

class PDFRAGTool_sumedh(BaseTool):
    name: str = "pdf_rag_search"
    description: str = "Answer questions strictly from the provided PDF using RAG."
    args_schema: Type[BaseModel] = PDFQuery

    def __init__(self, retriever, **data):
        super().__init__(**data)
        self._retriever = retriever

    def _run(self, query: str) -> str:
        return simple_rag_answer(self._retriever, query)
    
from crewai.tools import tool

@tool("Tool Name")
def my_simple_tool(question: str) -> str:
    """Tool description for clarity."""
    
    return "Tool output"


def make_pdf_tool(retriever):
    return PDFRAGTool_sumedh(retriever=retriever)


def run_with_crewai(retriever, question: str) -> str:
    pdf_tool = make_pdf_tool(retriever)

    researcher = Agent(
        role="PDF Research Agent",
        goal="Extract precise facts from the PDF and answer only using its content.",
        backstory="Experienced at reading resumes and technical PDFs.",
        verbose=False,
        allow_delegation=False,
        tools=[pdf_tool],
    )

    task = Task(
        description=f"Use the pdf_rag_search tool to answer: {question}\n"
                    f"If the PDF mentions pages, include page numbers.",
        agent=researcher,
        expected_output="A short, direct answer grounded only in the PDF."
    )

    crew = Crew(agents=[researcher], tasks=[task])
    return str(crew.kickoff())

if __name__ == "__main__":
    question = "What is my AIR and what is my CGPA as written in the PDF?"

    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"PDF not found at {PDF_PATH}")

    retriever = build_retriever(PDF_PATH)

    print("\n=== RAG answer (Ollama) ===")
    print(simple_rag_answer(retriever, question))

    print("\n=== CrewAI final answer ===")
    print(run_with_crewai(retriever, question))
