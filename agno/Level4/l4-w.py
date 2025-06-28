"""
Document Q&A Workflow Example using Agno, Gemini, and ChromaDB

This script demonstrates how to build an end-to-end workflow for question answering over the contents of a PDF document using the Agno framework and Gemini language model.

Workflow Overview:
- Loads environment variables and API keys from a .env file.
- Downloads and chunks a PDF from a specified URL.
- Embeds the PDF content using Gemini embeddings and stores them in a Chroma vector database.
- Defines a workflow class that:
    - Accepts user questions.
    - Searches the vector database for relevant information.
    - Uses a Gemini-powered agent to answer questions based on the PDF content.
    - Caches answers for repeated questions.
    - Handles API quota errors with exponential backoff and retry logic.
- Persists workflow state using SQLite storage.
- Launches an interactive Agno Playground web UI for users to ask questions about the PDF.
"""
import os
import time
from typing import  Dict
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google.gemini import Gemini
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase,PDFUrlReader
from agno.vectordb.chroma import ChromaDb
from agno.embedder.google import GeminiEmbedder
from agno.playground import Playground, serve_playground_app
from agno.run.response import RunEvent, RunResponse
from agno.storage.sqlite import SqliteStorage
from agno.utils.log import logger
from agno.workflow.workflow import Workflow
from google.genai.errors import ClientError  

# Load environment variables from .env file
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
agno_api_key = os.getenv("AGNO_API_KEY")

# Set up the embedder using Gemini
embedder = GeminiEmbedder(api_key=os.getenv("GOOGLE_API_KEY"))

# Load PDF into the vector database
logger.info("Loading and chunking PDF into vector DB...")
knowledge_base = PDFUrlKnowledgeBase(
    urls=["https://www.adobe.com/support/products/enterprise/knowledgecenter/media/c4611_sample_explain.pdf"],
    vector_db=ChromaDb(collection="doc", embedder=embedder),
    embedder=embedder,
    reader=PDFUrlReader(),
)
knowledge_base.load(recreate=False)
logger.info("Knowledge base loaded successfully.")


class DocumentQnAWorkflow(Workflow):
    """
    Workflow to process documents from URLs, optionally perform OCR, and answer user questions
    based on the embedded PDF content.

    Attributes:
        description (str): A short description of the workflow.
        cache (Dict[str, str]): A simple in-memory cache to store previously answered questions
            to avoid redundant processing.
        question_agent (Agent): An Agent configured to answer questions using the Gemini model
            with access to the knowledge base.
    """

    description: str = "Process document from URL, perform OCR if needed, and answer questions."
    cache: Dict[str, str] = {}

    question_agent: Agent = Agent(
        name="Question Answering Agent",
        instructions=["Answer user questions based on the embedded PDF content. "
                      "Use the knowledge base to find relevant information."],
        model=Gemini(),
        knowledge=knowledge_base,
        search_knowledge=True,
        add_history_to_messages=True,
        num_history_responses=3,
        show_tool_calls=True,
        exponential_backoff=True,
        delay_between_retries=5,
        monitoring=True,
    )

    def run(self, user_question: str) -> RunResponse:
        """
        Executes the Q&A workflow to answer a user's question.

        Args:
            user_question (str): The question asked by the user.

        Returns:
            RunResponse: The response from the agent, including status and content.

        Behavior:
            - Checks if the answer exists in the cache, returns cached answer if available.
            - Otherwise, sends the question to the agent for processing.
            - Handles Google API quota exhaustion by retrying after a wait.
            - Logs relevant info and errors during execution.
        """
        logger.info(f"Running Q&A workflow for question: {user_question}")

        # Check for cached response
        if user_question in self.cache:
            logger.info("Cache hit: returning cached response.")
            cached_answer = self.cache[user_question]
            return RunResponse(run_id=self.run_id, event=RunEvent.workflow_completed, content=cached_answer)

        try:
            logger.debug("Cache miss: processing through agent.")
            qa_response: RunResponse = self.question_agent.run(user_question)

            logger.info("Question answered successfully.")
            self.cache[user_question] = qa_response.content
            return RunResponse(run_id=self.run_id, event=RunEvent.workflow_completed, content=qa_response.content)

        except ClientError as e:
            if "RESOURCE_EXHAUSTED" in str(e):
                logger.warning("Quota exceeded (429 RESOURCE_EXHAUSTED). Retrying after 60 seconds...")
                time.sleep(60)  # Wait before retry
                try:
                    qa_response: RunResponse = self.question_agent.run(user_question)
                    logger.info("Retry successful.")
                    self.cache[user_question] = qa_response.content
                    return RunResponse(run_id=self.run_id, event=RunEvent.workflow_completed, content=qa_response.content)
                except Exception as retry_error:
                    logger.error(f"Retry also failed: {retry_error}")
                    return RunResponse(run_id=self.run_id, event=RunEvent.workflow_failed, content="Retry failed due to quota issues.")
            else:
                logger.error(f"ClientError occurred: {e}")
                return RunResponse(run_id=self.run_id, event=RunEvent.workflow_failed, content="Client error during QA.")
        except Exception as e:
            logger.error(f"Question answering failed: {e}")
            return RunResponse(run_id=self.run_id, event=RunEvent.workflow_failed, content="QA failed.")


# Initialize the workflow with persistent storage
document_qna_workflow = DocumentQnAWorkflow(
    name="Document Q&A Workflow",
    workflow_id="qna-session",
    storage=SqliteStorage(
        db_file="tmp/document.db",
        table_name="document_qna_run"
    ),
    monitoring=True,
)

# Launch the Agno Playground UI
app = Playground(workflows=[document_qna_workflow]).get_app()

if __name__ == "__main__":
    """
    Entrypoint for starting the Agno Playground app with the Document Q&A workflow.
    """
    logger.info("Starting the playground app...")
    serve_playground_app("l4-w:app")
