import os
import logfire
from pydantic import BaseModel, Field
from pydantic_ai import Agent, Tool
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider
import PyPDF2
import chromadb
from chromadb.utils import embedding_functions
from typing import Optional
import json
import asyncio
from dotenv import load_dotenv
import platform
import google.generativeai as genai
import uuid
import re
from image import try_with_retry

load_dotenv()

logfire_token = os.getenv('LOGFIRE_TOKEN')
if not logfire_token:
    print("Error: LOGFIRE_TOKEN not set in .env file.")
    logfire.error("LOGFIRE_TOKEN not set in Pdf.py")
    logfire_token = "dummy_token_if_not_set"
logfire.configure(token=logfire_token)
logfire.info("Starting Pdf.py module for PDF processing")

CHROMA_DB_PATH = "./chroma_db"
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
pdf_content_collection = chroma_client.get_or_create_collection(
    name="pdf_content", embedding_function=embedding_functions.DefaultEmbeddingFunction()
)

METADATA_FILE = "pdf_metadata.json"

def initialize_pdf_metadata():
    """Initializes an empty PDF metadata JSON file if it doesn't exist."""
    if not os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            logfire.info(f"Created {METADATA_FILE}")
        except Exception as e:
            logfire.error(f"Failed to create {METADATA_FILE}: {str(e)}")
    else:
        logfire.info(f"{METADATA_FILE} already exists")

initialize_pdf_metadata()

if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

def validate_pdf_file(pdf_path: str) -> bool:
    """
    Validates if a PDF file is accessible and valid.
    Checks file existence, format, and permissions.
    """
    norm_path = os.path.normpath(pdf_path)
    logfire.info(f"Validating PDF: {norm_path}")
    base_dir = os.path.dirname(norm_path)
    filename = os.path.basename(norm_path)
    if not os.path.exists(base_dir):
        logfire.error(f"Directory does not exist: {base_dir}")
        return False
    try:
        files_in_dir = os.listdir(base_dir)
        matching_files = [f for f in files_in_dir if f.lower() == filename.lower()]
        if not matching_files:
            logfire.error(f"PDF file does not exist: {norm_path}")
            return False
        actual_path = os.path.join(base_dir, matching_files[0])
        logfire.info(f"Found matching PDF file: {actual_path}")
        with open(actual_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            if len(reader.pages) == 0:
                logfire.error(f"PDF file {actual_path} is empty or corrupted")
                return False
            logfire.info(f"Valid PDF: Path={actual_path}, Pages={len(reader.pages)}")
            return True
    except PermissionError as e:
        logfire.error(f"Permission denied for {norm_path}: {str(e)}")
        return False
    except Exception as e:
        logfire.error(f"Invalid PDF file {norm_path}: {str(e)}")
        return False

def check_pdf_content_in_db(pdf_path: str) -> Optional[dict]:
    """
    Checks ChromaDB for existing PDF content by file path.
    Returns content and metadata if found, else None.
    """
    try:
        results = pdf_content_collection.get(where={"pdf_path": pdf_path}, limit=1, include=['documents', 'metadatas'])
        if results['ids']:
            logfire.info(f"Found PDF content in ChromaDB for {pdf_path}")
            return {
                'id': results['ids'][0],
                'content': results['documents'][0],
                'metadata': results['metadatas'][0]
            }
        logfire.info(f"No PDF content found in ChromaDB for {pdf_path}")
        return None
    except Exception as e:
        logfire.error(f"ChromaDB query failed for {pdf_path}: {str(e)}")
        return None

class PDFExtractionInput(BaseModel):
    """Pydantic model for PDF content extraction input."""
    pdf_path: str = Field(description="Path to the PDF file to extract content from.")
    output_file: Optional[str] = Field(None, description="Optional file path to save the extracted content locally.")

class PDFQueryInput(BaseModel):
    """Pydantic model for querying PDF content."""
    pdf_path: str = Field(description="Path to the PDF file to query.")
    question: str = Field(description="Question about the PDF content.")

def create_pdf_extraction_tool() -> Tool:
    """Creates a tool to extract text from PDF files."""
    async def extract_pdf_content(input_model: PDFExtractionInput) -> str:
        """
        Extracts text from a PDF file and stores it in ChromaDB.
        Optionally saves to a file and returns the extracted content.
        """
        pdf_path = input_model.pdf_path
        output_file = input_model.output_file
        logfire.info(f"Extracting content from PDF: {pdf_path}")

        if not validate_pdf_file(pdf_path):
            return f"Error: Invalid PDF: {pdf_path}. Ensure the file exists and is a valid PDF."

        existing_content = check_pdf_content_in_db(pdf_path)
        if existing_content:
            content_text = existing_content['content']
            if output_file:
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(content_text)
                    logfire.info(f"PDF content retrieved from ChromaDB and saved to {output_file}")
                except IOError as io_e:
                    logfire.error(f"Could not save PDF content to {output_file}: {io_e}")
            return content_text

        try:
            norm_path = os.path.normpath(pdf_path)
            base_dir = os.path.dirname(norm_path)
            filename = os.path.basename(norm_path)
            files_in_dir = os.listdir(base_dir)
            matching_files = [f for f in files_in_dir if f.lower() == filename.lower()]
            if not matching_files:
                return f"Error: PDF file does not exist: {norm_path}"
            actual_path = os.path.join(base_dir, matching_files[0])

            with open(actual_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                content_text = ""
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        content_text += text + " "
                content_text = content_text.strip()
                if not content_text:
                    logfire.warning(f"No text extracted from PDF: {pdf_path}")
                    return f"Error: No text extracted from {pdf_path}. The PDF may be scanned or image-based."

            content_text = re.sub(r'\s+', ' ', content_text).strip()
            unique_id = str(uuid.uuid4())
            pdf_content_collection.add(
                documents=[content_text],
                metadatas=[{'pdf_path': pdf_path, 'source': 'pdf_extraction'}],
                ids=[unique_id]
            )
            logfire.info(f"PDF content stored in ChromaDB for {pdf_path}, ID: {unique_id}")

            if output_file:
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(content_text)
                    logfire.info(f"PDF content saved to {output_file}")
                except IOError as io_e:
                    logfire.error(f"Could not save PDF content to {output_file}: {io_e}")

            try:
                with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except FileNotFoundError:
                metadata = {}
                logfire.warning(f"{METADATA_FILE} not found, creating new")

            metadata[unique_id] = {'path': pdf_path, 'content': content_text}
            try:
                with open(METADATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
                logfire.info(f"Saved metadata to {METADATA_FILE} for {pdf_path}")
            except Exception as e:
                logfire.error(f"Failed to save metadata for {pdf_path}: {str(e)}")

            return content_text
        except Exception as e:
            logfire.error(f"Failed to extract PDF content for {pdf_path}: {str(e)}")
            return f"Error: Failed to extract PDF content for {pdf_path}: {str(e)}"

    return Tool[PDFExtractionInput](
        name="extract_pdf_content",
        description="Extracts text from a PDF file, stores it in ChromaDB, and optionally saves to a file.",
        function=extract_pdf_content
    )

def create_pdf_query_tool() -> Tool:
    """Creates a tool to answer questions about PDF content."""
    async def query_pdf_content(input_model: PDFQueryInput) -> str:
        """
        Answers a question about a PDF using its stored content.
        Uses Gemini model to generate a concise answer.
        """
        pdf_path = input_model.pdf_path
        question = input_model.question
        logfire.info(f"Answering question for PDF: {pdf_path}, Question: {question}")

        if not validate_pdf_file(pdf_path):
            return f"Error: Invalid PDF: {pdf_path}. Ensure the file exists and is a valid PDF."

        existing_content = check_pdf_content_in_db(pdf_path)
        if not existing_content:
            logfire.warning(f"No content found for {pdf_path}. Run 'extract_pdf_content' first.")
            return f"Error: No content found for {pdf_path}. Please extract the content first using 'extract_pdf_content'."

        try:
            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
            model = genai.GenerativeModel('gemini-1.5-flash')

            async def query():
                prompt = (
                    f"Based on the following PDF content, answer the question: {question}\n\n"
                    f"Content:\n{existing_content['content']}\n\n"
                    "Provide a concise and accurate answer (50-100 words) based only on the content. "
                    "If the content lacks details to answer the question, state that clearly."
                )
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: model.generate_content([prompt])
                )
                answer = response.text
                word_count = len(answer.split())
                if word_count > 100:
                    raise ValueError(f"Answer length {word_count} words exceeds 100-word limit.")
                return answer

            answer = await try_with_retry(query)
            logfire.info(f"Answered question for {pdf_path}: {answer[:50]}...")
            return answer
        except Exception as e:
            logfire.error(f"PDF query failed for {pdf_path}: {str(e)}")
            return f"Error: Failed to answer question for {pdf_path}: {str(e)}"

    return Tool[PDFQueryInput](
        name="query_pdf_content",
        description="Answers a question about a PDF using its stored content from ChromaDB.",
        function=query_pdf_content
    )

class PDFAgent(Agent):
    """
    Specialized agent for extracting and querying PDF content.
    Uses PyPDF2 for extraction and Gemini for summarization and queries.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key  # Store api_key as instance attribute
        super().__init__(
            model=GeminiModel('gemini-1.5-flash-latest', provider=GoogleGLAProvider(api_key=api_key)),
            api_key=api_key,
            tools=[
                create_pdf_extraction_tool(),
                create_pdf_query_tool()
            ],
            system_prompt=(
                'You are an expert PDF content assistant capable of extracting text and answering questions. '
                '1. **Content Extraction**: Use the `extract_pdf_content` tool to extract text from PDFs and store in ChromaDB. '
                '2. **Summarization**: Summarize PDF content (150-250 words) when requested, focusing on main points. '
                '3. **Question Answering**: Use the `query_pdf_content` tool to answer questions based on stored content. '
                '4. **Error Handling**: Provide clear error messages for invalid PDFs, missing content, or API issues. '
                'Store extracted content in ChromaDB and pdf_metadata.json with path metadata.'
            )
        )
        self.pdf_content_collection = pdf_content_collection

    async def summarize_pdf(self, pdf_path: str, length: str = "150-250 words") -> str:
        """
        Summarizes the content of a PDF file.
        Extracts content and uses Gemini model to generate a summary.
        """
        logfire.info(f"Summarizing PDF: {pdf_path}, Length: {length}")
        if not validate_pdf_file(pdf_path):
            return f"Error: Invalid PDF: {pdf_path}. Ensure the file exists and is a valid PDF."

        existing_content = check_pdf_content_in_db(pdf_path)
        if not existing_content:
            extract_response = await self.run(f"extract_pdf_content(pdf_path='{pdf_path}')")
            content = await self._extract_response_content(extract_response)
            if "Error" in content:
                return content
        else:
            content = existing_content['content']

        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')

            async def summarize():
                prompt = (
                    f"Summarize the following PDF content in {length}, focusing on main points and key takeaways:\n\n"
                    f"Content:\n{content}\n\n"
                    "Ensure the summary is concise, accurate, and avoids extraneous details."
                )
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: model.generate_content([prompt])
                )
                summary = response.text
                word_count = len(summary.split())
                if word_count < 150 or word_count > 250:
                    raise ValueError(f"Summary length {word_count} words is outside {length} range.")
                return summary

            summary = await try_with_retry(summarize)
            logfire.info(f"Summary generated for {pdf_path}: {summary[:50]}...")
            return summary
        except Exception as e:
            logfire.error(f"PDF summarization failed for {pdf_path}: {str(e)}")
            return f"Error: Failed to summarize PDF {pdf_path}: {str(e)}"

    async def answer_question(self, pdf_path: str, question: str) -> str:
        """
        Answers a question about a PDF using its stored content.
        Delegates to the query_pdf_content tool.
        """
        logfire.info(f"Answering question for PDF: {pdf_path}, Question: {question}")
        query_response = await self.run(f"query_pdf_content(pdf_path='{pdf_path}', question='{question}')")
        return await self._extract_response_content(query_response)

async def try_with_retry(operation, max_attempts=5, base_delay=3):
    """
    Retries an async operation with exponential backoff.
    Handles API errors like 429/503 with retries.
    """
    for attempt in range(max_attempts):
        try:
            return await operation()
        except Exception as e:
            if any(code in str(e) for code in ["429", "503"]) and attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                logfire.warn(f"API error on attempt {attempt + 1}, retrying after {delay}s", error=str(e))
                await asyncio.sleep(delay)
            else:
                logfire.error(f"Operation failed after {attempt + 1} attempts", error=str(e))
                raise Exception(f"Error: API unavailable (429/503) or other error. Please check your Gemini API quota at https://console.cloud.google.com/apis/api/aiplatform.googleapis.com/quotas or try again later: {str(e)}")
    raise Exception(f"Error: API unavailable (429/503) after {max_attempts} attempts.")