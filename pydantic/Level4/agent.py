import os
import json
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent, Tool
from PyPDF2 import PdfReader
import chromadb
from chromadb.utils import embedding_functions
import uuid
import logfire

class PdfExtractionInput(BaseModel):
    """Input model for PDF extraction.

    Attributes:
        pdf_path (str): Local file path of the PDF to extract.
    """
    pdf_path: str = Field(description="Local file path of the PDF to extract.")

class QueryInput(BaseModel):
    """Input model for querying PDF content.

    Attributes:
        pdf_path (str): Local file path of the PDF to query.
        question (str): Question about the PDF content.
    """
    pdf_path: str = Field(description="PDF file path to query.")
    question: str = Field(description="Question about the PDF content.")

class PdfExtractionAgent:
    """Agent for extracting text from PDFs and storing it in ChromaDB."""
    
    def __init__(self, api_key: str):
        """Initialize the extraction agent with API key.

        Sets up ChromaDB client, embedding function, metadata file, and configures
        the agent with the extraction tool.

        """
        self.client = chromadb.Client()
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name='all-MiniLM-L6-v2')
        self.metadata_file = "pdf_metadata.json"
        
        self.agent = Agent(
            model='google-gla:gemini-1.5-pro',
            api_key=api_key,
            tools=[self._create_extraction_tool()],
            system_prompt=(
                'You are an expert at extracting content from PDF files. '
                'Use the `extract_pdf` tool to process the PDF and store its content in ChromaDB. '
                'Ensure all text is extracted accurately and stored with metadata.'
            )
        )

    def _validate_pdf_file(self, pdf_path: str) -> bool:
        """Validate if the provided file is a valid PDF.

        Checks if the file exists, has a .pdf extension, and can be read by PyPDF2.

        Args:
            pdf_path (str): Path to the PDF file.

        Returns:
            bool: True if the file is a valid PDF, False otherwise.
        """
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

    def _extract_pdf_text(self, pdf_path: str) -> list[str]:
        """Extract and chunk text from a PDF file.

        Reads the PDF, extracts text from each page, and splits it into chunks of approximately 500 characters.

        Args:
            pdf_path (str): Path to the PDF file.

        Returns:
            list[str]: List of text chunks extracted from the PDF.
        """
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

    def _store_in_chromadb(self, pdf_path: str, chunks: list[str]) -> Optional[str]:
        """Store text chunks in ChromaDB.

        Creates a new collection with a unique name and stores the text chunks with generated IDs.

        Args:
            pdf_path (str): Path to the PDF file, used to generate collection name.
            chunks (list[str]): List of text chunks to store.

        Returns:
            Optional[str]: Name of the created collection, or None if storage fails.
        """
        try:
            collection_name = f"pdf_{os.path.basename(pdf_path).replace('.pdf', '')}_{uuid.uuid4().hex[:8]}"
            collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            ids = [f"chunk_{i}" for i in range(len(chunks))]
            collection.add(documents=chunks, ids=ids)
            logfire.info(f"Stored {len(chunks)} chunks in ChromaDB collection: {collection_name}")
            return collection_name
        except Exception as e:
            logfire.error(f"Failed to store chunks in ChromaDB: {str(e)}")
            return None

    def _save_metadata(self, pdf_path: str, collection_name: str):
        """Save metadata for the processed PDF, overwriting existing entry.

        Updates the metadata file with the PDF path, collection name, and timestamp,
        removing any existing entry for the same PDF.

        Args:
            pdf_path (str): Path to the PDF file.
            collection_name (str): Name of the ChromaDB collection.
        """
        try:
            metadata = []
            if os.path.exists(self.metadata_file):
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            # Remove any existing entry for this PDF
            metadata = [entry for entry in metadata if entry['pdf_path'] != pdf_path]
            # Add new entry
            entry = {
                'pdf_path': pdf_path,
                'collection_name': collection_name,
                'timestamp': datetime.now().isoformat()
            }
            metadata.append(entry)
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            logfire.info(f"Saved metadata for {pdf_path} to {self.metadata_file}")
        except Exception as e:
            logfire.error(f"Failed to save metadata: {str(e)}")

    def _load_metadata(self, pdf_path: str) -> Optional[dict]:
        """Load metadata for a PDF.

        Retrieves metadata entry for the specified PDF from the metadata file.

        Args:
            pdf_path (str): Path to the PDF file.

        Returns:
            Optional[dict]: Metadata dictionary if found, None otherwise.
        """
        try:
            if not os.path.exists(self.metadata_file):
                logfire.info(f"Metadata file not found: {self.metadata_file}")
                return None
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
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

    def is_pdf_extracted(self, pdf_path: str) -> bool:
        """Check if the PDF has already been extracted and stored.

        Verifies if metadata exists for the PDF and if the associated ChromaDB collection is valid.

        Args:
            pdf_path (str): Path to the PDF file.

        Returns:
            bool: True if the PDF is extracted and the collection exists, False otherwise.
        """
        metadata = self._load_metadata(pdf_path)
        if metadata:
            try:
                # Verify the collection still exists in ChromaDB
                self.client.get_collection(
                    name=metadata['collection_name'],
                    embedding_function=self.embedding_function
                )
                return True
            except Exception:
                logfire.warn(f"Collection {metadata['collection_name']} not found for {pdf_path}")
                return False
        return False

    def _create_extraction_tool(self) -> Tool:
        """Create a tool for PDF extraction.

        Defines a tool that validates, extracts, and stores PDF content in ChromaDB.

        Returns:
            Tool: Configured extraction tool for the agent.
        """
        def extract_pdf(input_model: PdfExtractionInput) -> str:
            pdf_path = input_model.pdf_path
            logfire.info(f"Extracting content from: {pdf_path}")
            if not self._validate_pdf_file(pdf_path):
                return f"Error: Invalid PDF file: {pdf_path}"
            chunks = self._extract_pdf_text(pdf_path)
            if not chunks:
                return f"Error: No text extracted from {pdf_path}"
            collection_name = self._store_in_chromadb(pdf_path, chunks)
            if not collection_name:
                return f"Error: Failed to store content in ChromaDB"
            self._save_metadata(pdf_path, collection_name)
            return f"Successfully extracted and stored content from {pdf_path}"
        return Tool[PdfExtractionInput](
            name="extract_pdf",
            description="Extracts text from a PDF and stores it in ChromaDB.",
            function=extract_pdf
        )

    async def extract_pdf(self, pdf_path: str) -> str:
        """Extract content from a PDF and store it in ChromaDB.

        Runs the agent to process the PDF using the extraction tool.

        Args:
            pdf_path (str): Path to the PDF file.

        Returns:
            str: Result message indicating success or failure.
        """
        response = await self.agent.run(f"Extract content from the PDF at {pdf_path}")
        return response.output if hasattr(response, 'output') else str(response)

class PdfQueryAgent:
    """Agent for querying PDF content stored in ChromaDB."""
    
    def __init__(self, api_key: str):
        """Initialize the query agent with API key.

        Sets up ChromaDB client, embedding function, metadata file, and configures
        the agent with the query tool.

        Args:
            api_key (str): API key for the Gemini model.
        """
        self.client = chromadb.Client()
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name='all-MiniLM-L6-v2')
        self.metadata_file = "pdf_metadata.json"
        
        self.agent = Agent(
            model='google-gla:gemini-1.5-pro',
            api_key=api_key,
            tools=[self._create_query_tool()],
            system_prompt=(
                'You are an expert at answering questions about PDF content. '
                'Use the `query_pdf_content` tool to retrieve relevant content from ChromaDB. '
                'Provide a concise summary (1-2 sentences) based only on the retrieved content. '
                'If no relevant content is found, state so and suggest re-extraction.'
            )
        )

    def _load_metadata(self, pdf_path: str) -> Optional[dict]:
        """Load metadata for a PDF.

        Retrieves metadata entry for the specified PDF from the metadata file.

        Args:
            pdf_path (str): Path to the PDF file.

        Returns:
            Optional[dict]: Metadata dictionary if found, None otherwise.
        """
        try:
            if not os.path.exists(self.metadata_file):
                logfire.info(f"Metadata file not found: {self.metadata_file}")
                return None
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
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

    def _create_query_tool(self) -> Tool:
        """Create a tool for querying PDF content.

        Defines a tool that retrieves relevant text chunks from ChromaDB to answer questions.

        Returns:
            Tool: Configured query tool for the agent.
        """
        def query_pdf_content(input_model: QueryInput) -> str:
            pdf_path = input_model.pdf_path
            question = input_model.question
            logfire.info(f"Answering question '{question}' for PDF: {pdf_path}")
            metadata = self._load_metadata(pdf_path)
            if not metadata:
                return f"Error: No content found for {pdf_path}. Please extract the PDF first."
            collection_name = metadata['collection_name']
            try:
                collection = self.client.get_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function
                )
                results = collection.query(query_texts=[question], n_results=3)
                relevant_chunks = results['documents'][0]
                if not relevant_chunks:
                    logfire.warn(f"No relevant content found for question: {question}")
                    return f"No relevant content found for the question. Please try re-extracting the PDF with --force-extract."
                context = "\n".join(relevant_chunks)
                logfire.info(f"Retrieved {len(relevant_chunks)} chunks for question")
                return f"Summary: {context[:200]}..." if len(context) > 200 else f"Summary: {context}"
            except Exception as e:
                logfire.error(f"Failed to query ChromaDB: {str(e)}")
                return f"Error: Failed to retrieve content for {pdf_path}. Please try re-extracting the PDF with --force-extract."
        return Tool[QueryInput](
            name="query_pdf_content",
            description="Retrieves PDF content from ChromaDB to answer questions.",
            function=query_pdf_content
        )

    async def query_pdf(self, pdf_path: str, question: str) -> str:
        """Query the content of a PDF to answer a question.

        Runs the agent to retrieve and summarize relevant content for the given question.

        Args:
            pdf_path (str): Path to the PDF file.
            question (str): Question about the PDF content.

        Returns:
            str: Summary of relevant content or error message.
        """
        response = await self.agent.run(f"Using the content from {pdf_path}, answer: {question}")
        return response.output if hasattr(response, 'output') else str(response)