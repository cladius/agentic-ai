from agno.agent import Agent
from agno.models.google import Gemini
from agno.knowledge.pdf_url import PDFUrlReader

# Create the PDF Processing Agent
# This agent is designed to process PDF content from a URL, summarize it, or answer questions
# based on the content. It uses the PDFUrlReader tool to fetch and read PDF files.
# The agent is configured to handle errors gracefully and return a specific message if processing fails.
def create_pdf_agent(knowledge_base):
    return Agent(
        name="PDF Processor",
        model=Gemini(),
        knowledge=knowledge_base,
        search_knowledge=True,
        tools=[PDFUrlReader()],
        instructions=[
            "Query the knowledge base for PDF content at the provided URL.",
            "Summarize or answer questions (max 1500 characters).",
            "If query fails, return: 'Failed to process PDF: {error}'."
        ],
        debug_mode=True,
    )