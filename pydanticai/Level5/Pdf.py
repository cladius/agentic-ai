import os
import asyncio
import platform
import json
import argparse
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
import logfire
from pydantic import BaseModel, Field
from pydantic_ai import Agent, Tool
import chromadb
from chromadb.utils import embedding_functions
from PyPDF2 import PdfReader
import uuid
# Load environment variables
load_dotenv()

# Initialize Logfire
logfire_token = os.getenv('LOGFIRE_TOKEN')
if not logfire_token:
    print("Error: LOGFIRE_TOKEN not set in .env file.")
    exit(1)
logfire.configure(token=logfire_token)
logfire.info("Starting pdf.py - PDF Processing Script")

# Fix Windows event loop
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ChromaDB setup
CHROMA_DB_PATH = "./chroma_db"
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
pdf_collection = chroma_client.get_or_create_collection(
    name="pdf_content", embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(model_name='all-MiniLM-L6-v2')
)

# Metadata file
PDF_METADATA_FILE = "pdf_metadata.json"

class PdfExtractionInput(BaseModel):
    pdf_path: str = Field(description="Local file path of the PDF to extract.")

class QueryInput(BaseModel):
    pdf_path: str = Field(description="PDF file path to query.")
    question: str = Field(description="Question about the PDF content.")

def validate_pdf_file(pdf_path: str) -> bool:
    supported_extensions = {'.pdf'}
    if not os.path.isfile(pdf_path):
        logfire.error(f"PDF file does not exist: {pdf_path}")
        return False
    ext = os.path.splitext(pdf_path)[1].lower()
    if ext not in supported_extensions:
        logfire.error(f"Unsupported file format: {pdf_path}. Supported: {supported_extensions}")
        return False
    try:
        with open(pdf_path, 'rb') as f:
            PdfReader(f)
        logfire.info(f"Validated PDF: {pdf_path}")
        return True
    except Exception as e:
        logfire.error(f"Invalid PDF {pdf_path}: {str(e)}")
        return False

def extract_pdf_text(pdf_path: str) -> list[str]:
    try:
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            text_chunks = []
            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                if not text.strip():
                    logfire.warn(f"No text extracted from page {page_num} of {pdf_path}")
                    continue
                chunk_size = 500
                for i in range(0, len(text), chunk_size):
                    chunk = text[i:i+chunk_size].strip()
                    if chunk:
                        text_chunks.append(chunk)
            logfire.info(f"Extracted {len(text_chunks)} chunks from {pdf_path}")
            return text_chunks
    except Exception as e:
        logfire.error(f"Failed to extract text from {pdf_path}: {str(e)}")
        return []

def store_in_chromadb(pdf_path: str, chunks: list[str]) -> Optional[str]:
    try:
        collection_name = f"pdf_{os.path.basename(pdf_path).replace('.pdf', '')}_{uuid.uuid4().hex[:8]}"
        collection = pdf_collection
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        collection.add(
            documents=chunks,
            metadatas=[{"pdf_path": pdf_path} for _ in chunks],
            ids=ids
        )
        logfire.info(f"Stored {len(chunks)} chunks in ChromaDB collection: {collection_name}")
        return collection_name
    except Exception as e:
        logfire.error(f"Failed to store chunks in ChromaDB: {str(e)}")
        return None

def save_pdf_metadata(pdf_path: str, collection_name: str):
    try:
        metadata = []
        if os.path.exists(PDF_METADATA_FILE):
            with open(PDF_METADATA_FILE, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        entry = {
            'pdf_path': pdf_path,
            'collection_name': collection_name,
            'timestamp': datetime.now().isoformat()
        }
        metadata.append(entry)
        with open(PDF_METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        logfire.info(f"Saved metadata for {pdf_path} to {PDF_METADATA_FILE}")
    except Exception as e:
        logfire.error(f"Failed to save metadata: {str(e)}")

def load_pdf_metadata(pdf_path: str) -> Optional[dict]:
    try:
        if not os.path.exists(PDF_METADATA_FILE):
            logfire.info(f"Metadata file not found: {PDF_METADATA_FILE}")
            return None
        with open(PDF_METADATA_FILE, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        for entry in metadata:
            if entry['pdf_path'] == pdf_path:
                logfire.info(f"Found metadata for PDF: {pdf_path}")
                return entry
        logfire.info(f"No metadata found for PDF: {pdf_path}")
        return None
    except Exception as e:
        logfire.error(f"Failed to load metadata: {str(e)}")
        return None

def create_pdf_extraction_tool() -> Tool:
    def extract_pdf(input_model: PdfExtractionInput) -> str:
        pdf_path = input_model.pdf_path
        logfire.info(f"Extracting content from: {pdf_path}")
        if not validate_pdf_file(pdf_path):
            return f"Error: Invalid PDF file: {pdf_path}"
        chunks = extract_pdf_text(pdf_path)
        if not chunks:
            return f"Error: No text extracted from {pdf_path}"
        collection_name = store_in_chromadb(pdf_path, chunks)
        if not collection_name:
            return f"Error: Failed to store content in ChromaDB"
        save_pdf_metadata(pdf_path, collection_name)
        return "\n".join(chunks)
    return Tool[PdfExtractionInput](
        name="extract_pdf",
        description="Extracts text from a PDF and stores it in ChromaDB. Returns the extracted content.",
        function=extract_pdf
    )

def create_pdf_query_tool() -> Tool:
    def query_pdf_content(input_model: QueryInput) -> str:
        pdf_path = input_model.pdf_path
        question = input_model.question
        logfire.info(f"Answering question '{question}' for PDF: {pdf_path}")
        metadata = load_pdf_metadata(pdf_path)
        if not metadata:
            return f"Error: No content found for {pdf_path}. Extract PDF first."
        try:
            collection = pdf_collection
            results = collection.query(
                query_texts=[question],
                n_results=3,
                where={"pdf_path": pdf_path}
            )
            relevant_chunks = results['documents'][0]
            if not relevant_chunks:
                logfire.warn(f"No relevant content found for question: {question}")
                return f"Error: No relevant content found for the question."
            context = "\n".join(relevant_chunks)
            logfire.info(f"Retrieved {len(relevant_chunks)} chunks for question")
            return context
        except Exception as e:
            logfire.error(f"Failed to query ChromaDB: {str(e)}")
            return f"Error: Failed to retrieve content for {pdf_path}"
    return Tool[QueryInput](
        name="query_pdf_content",
        description="Retrieves PDF content from ChromaDB to answer questions.",
        function=query_pdf_content
    )

class PDFAgent(Agent):
    def __init__(self, api_key: str):
        super().__init__(
            model='google-gla:gemini-1.5-pro',
            api_key=api_key,
            tools=[create_pdf_extraction_tool(), create_pdf_query_tool()],
            system_prompt=(
                'You are an expert at extracting and querying content from PDF files. '
                'Use `extract_pdf` to extract and store PDF content in ChromaDB. '
                'Use `query_pdf_content` to answer questions based on stored content. '
                'For summarization, use the extracted content to generate a concise summary (150-250 words unless specified).'
            )
        )

    async def extract_pdf_content(self, pdf_path: str) -> str:
        response = await self.run(f"extract_pdf(pdf_path='{pdf_path}')")
        return await self._extract_response_content(response)

    async def summarize_pdf(self, pdf_path: str, length: str = "150-250 words") -> str:
        extracted_content = await self.extract_pdf_content(pdf_path)
        if "Error" in extracted_content:
            return extracted_content
        summary_response = await self.run(
            f"Summarize the following content in {length}, focusing on main points:\n{extracted_content[:2000]}"
        )
        return await self._extract_response_content(summary_response)

    async def answer_question(self, pdf_path: str, question: str) -> str:
        query_response = await self.run(
            f"query_pdf_content(pdf_path='{pdf_path}', question='{question}')"
        )
        return await self._extract_response_content(query_response)

    async def _extract_response_content(self, response) -> str:
        try:
            if hasattr(response, 'output'):
                output = response.output
                if isinstance(output, dict):
                    for key in ['summary', 'content', 'text', 'output', 'message']:
                        if key in output and isinstance(output[key], str):
                            return output[key]
                    return str(output.get('summary', str(output)))
                elif isinstance(output, str):
                    return output
                else:
                    return str(output)
            return str(response)
        except Exception as e:
            logfire.error(f"Failed to extract response content: {str(e)}")
            return f"Error: Failed to extract content: {str(e)}"

async def main():
    parser = argparse.ArgumentParser(description="PDF Processing Script")
    parser.add_argument("pdf_path", type=str, help="Path to PDF file (e.g., document.pdf)")
    parser.add_argument("--task", type=str, choices=["summarize", "extract"], default="summarize", help="Task: summarize or extract")
    parser.add_argument("--question", type=str, help="Question about the PDF content")
    args = parser.parse_args()

    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        logfire.error("GEMINI_API_KEY not set")
        print("Error: GEMINI_API_KEY not set in .env file.")
        return

    if not validate_pdf_file(args.pdf_path):
        print(f"Error: Invalid PDF file: {args.pdf_path}")
        return

    agent = PDFAgent(api_key=gemini_api_key)

    try:
        if args.question:
            print(f"\nAnswering question: {args.question}")
            result = await agent.answer_question(args.pdf_path, args.question)
            print(f"\nAnswer: {result}")
        elif args.task == "summarize":
            print(f"\nSummarizing PDF: {args.pdf_path}")
            result = await agent.summarize_pdf(args.pdf_path)
            print(f"\nSummary: {result}")
        elif args.task == "extract":
            print(f"\nExtracting content from PDF: {args.pdf_path}")
            result = await agent.extract_pdf_content(args.pdf_path)
            print(f"\nExtracted Content: {result[:2000]}...")
    except Exception as e:
        logfire.error(f"Error: {str(e)}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())