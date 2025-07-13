import os
import argparse
import asyncio
import platform
import json
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, Tool
import logfire
from PyPDF2 import PdfReader
from chromadb import Client
from chromadb.utils import embedding_functions
import uuid

# Load environment variables
load_dotenv()

# Initialize Logfire
logfire_token = os.getenv('LOGFIRE_TOKEN')
if not logfire_token:
    print("Error: LOGFIRE_TOKEN not set in .env file.")
    exit(1)
logfire.configure(token=logfire_token)
logfire.info("Starting PDF Q&A script")

# Fix Windows event loop
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Metadata file
METADATA_FILE = "pdf_metadata.json"

# ChromaDB client
CHROMA_CLIENT = Client()

# Embedding function
EMBEDDING_FUNCTION = embedding_functions.SentenceTransformerEmbeddingFunction(model_name='all-MiniLM-L6-v2')

# Input models
class PdfExtractionInput(BaseModel):
    pdf_path: str = Field(description="Local file path of the PDF to extract.")

class QueryInput(BaseModel):
    pdf_path: str = Field(description="PDF file path to query.")
    question: str = Field(description="Question about the PDF content.")

# Validate PDF file
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

# Extract and chunk text from PDF
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
                # Chunk text into ~500 char segments
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

# Store chunks in ChromaDB
def store_in_chromadb(pdf_path: str, chunks: list[str]) -> Optional[str]:
    try:
        collection_name = f"pdf_{os.path.basename(pdf_path).replace('.pdf', '')}_{uuid.uuid4().hex[:8]}"
        collection = CHROMA_CLIENT.get_or_create_collection(
            name=collection_name,
            embedding_function=EMBEDDING_FUNCTION
        )
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        collection.add(
            documents=chunks,
            ids=ids
        )
        logfire.info(f"Stored {len(chunks)} chunks in ChromaDB collection: {collection_name}")
        return collection_name
    except Exception as e:
        logfire.error(f"Failed to store chunks in ChromaDB: {str(e)}")
        return None

# Save metadata
def save_metadata(pdf_path: str, collection_name: str):
    try:
        metadata = []
        if os.path.exists(METADATA_FILE):
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        entry = {
            'pdf_path': pdf_path,
            'collection_name': collection_name,
            'timestamp': datetime.now().isoformat()
        }
        metadata.append(entry)
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        logfire.info(f"Saved metadata for {pdf_path} to {METADATA_FILE}")
    except Exception as e:
        logfire.error(f"Failed to save metadata: {str(e)}")

# Load metadata
def load_metadata(pdf_path: str) -> Optional[dict]:
    try:
        if not os.path.exists(METADATA_FILE):
            logfire.info(f"Metadata file not found: {METADATA_FILE}")
            return None
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
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

# PDF Extraction Tool
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
        save_metadata(pdf_path, collection_name)
        return f"Successfully extracted and stored content from {pdf_path}"
    return Tool[PdfExtractionInput](
        name="extract_pdf",
        description="Extracts text from a PDF and stores it in ChromaDB.",
        function=extract_pdf
    )

# PDF Query Tool
def create_pdf_query_tool() -> Tool:
    def query_pdf_content(input_model: QueryInput) -> str:
        pdf_path = input_model.pdf_path
        question = input_model.question
        logfire.info(f"Answering question '{question}' for PDF: {pdf_path}")
        metadata = load_metadata(pdf_path)
        if not metadata:
            return f"Error: No content found for {pdf_path}. Extract PDF first."
        collection_name = metadata['collection_name']
        try:
            collection = CHROMA_CLIENT.get_collection(
                name=collection_name,
                embedding_function=EMBEDDING_FUNCTION
            )
            results = collection.query(
                query_texts=[question],
                n_results=3
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

# Main execution
async def main():
    parser = argparse.ArgumentParser(description="Extract PDF content and answer questions.")
    parser.add_argument("pdf_path", type=str, help="Local file path of the PDF (e.g., document.pdf).")
    args = parser.parse_args()

    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        logfire.error("GEMINI_API_KEY not set")
        print("Error: GEMINI_API_KEY not set in .env file.")
        exit(1)

    if not validate_pdf_file(args.pdf_path):
        print(f"Error: Invalid PDF file: {args.pdf_path}")
        exit(1)

    try:
        extraction_tool = create_pdf_extraction_tool()
        query_tool = create_pdf_query_tool()

        # Extraction Agent
        extraction_agent = Agent(
            model='google-gla:gemini-1.5-pro',
            api_key=gemini_api_key,
            tools=[extraction_tool],
            system_prompt=(
                'You are an expert at extracting content from PDF files. '
                'Use the `extract_pdf` tool to process the PDF and store its content in ChromaDB. '
                'Ensure all text is extracted accurately and stored with metadata.'
            )
        )

        # Extract PDF
        logfire.info(f"Attempting to extract PDF: {args.pdf_path}")
        print(f"\nAttempting to extract PDF: {args.pdf_path}\n")
        extraction_response = await extraction_agent.run(
            f"Extract content from the PDF at {args.pdf_path}"
        )
        extraction_output = extraction_response.output if hasattr(extraction_response, 'output') else str(extraction_response)
        logfire.info(f"Extraction result: {extraction_output}")
        print("\n--- PDF Extraction ---")
        print(extraction_output)

        if "Error" in extraction_output:
            return

        # Query Agent
        query_agent = Agent(
            model='google-gla:gemini-1.5-pro',
            api_key=gemini_api_key,
            tools=[query_tool],
            system_prompt=(
                'You are an expert at answering questions about PDF content. '
                'Use the `query_pdf_content` tool to retrieve relevant content from ChromaDB. '
                'Provide a concise summary (1-2 sentences) based only on the retrieved content. '
                'If no relevant content is found, state so and suggest re-extraction.'
            )
        )

        # Interactive Q&A
        print("\n--- Interactive Q&A ---")
        print(f"PDF processed: {args.pdf_path}. Ask questions or type 'exit' to quit.")
        while True:
            question = input("Question: ").strip()
            if question.lower() == 'exit':
                logfire.info("Exiting Q&A session")
                print("Exiting Q&A session.")
                break
            logfire.info(f"User asked: {question}")
            query_response = await query_agent.run(
                f"Using the content from {args.pdf_path}, answer: {question}"
            )
            query_output = query_response.output if hasattr(query_response, 'output') else str(query_response)
            logfire.info(f"Query response: {query_output}")
            print(f"Answer: {query_output}\n")

    except Exception as e:
        logfire.error(f"Unexpected error: {str(e)}")
        print(f"\nError: {e}")
        print("Troubleshooting:")
        print("1. Verify PDF is readable and contains text (not scanned).")
        print("2. Check GEMINI_API_KEY and LOGFIRE_TOKEN in .env.")
        print(f"3. Delete {METADATA_FILE} and ./chroma_db if issues persist.")
        print("4. Install dependencies: pip install pydantic-ai==0.2.17 python-dotenv logfire PyPDF2 chromadb sentence-transformers")
        print("5. Share terminal output and Logfire logs for help.")

if __name__ == "__main__":
    asyncio.run(main())