import os
import argparse
import asyncio
import platform
from dotenv import load_dotenv
import logfire
from agent import PdfExtractionAgent, PdfQueryAgent

def setup_environment():
    """Configure environment variables and logging.

    Loads environment variables from .env file, configures Logfire for logging,
    and sets Windows event loop policy if necessary.

    Raises:
        ValueError: If LOGFIRE_TOKEN is not set in the .env file.
    """
    load_dotenv()
    logfire_token = os.getenv('LOGFIRE_TOKEN')
    if not logfire_token:
        raise ValueError("LOGFIRE_TOKEN not set in .env file.")
    logfire.configure(token=logfire_token)
    logfire.info("Starting PDF Q&A script")

    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def main():
    """Orchestrate PDF extraction and interactive Q&A session.

    Parses command-line arguments, initializes agents, extracts PDF content if needed,
    and handles user questions in an interactive loop.

    Args:
        None (uses command-line arguments for pdf_path and extract content from the pdf_path).

    Raises:
        ValueError: If GEMINI_API_KEY is not set in the .env file.
        Exception: For unexpected errors during execution, with troubleshooting guidance.
    """
    setup_environment()

    parser = argparse.ArgumentParser(description="Extract PDF content and answer questions.")
    parser.add_argument("pdf_path", type=str, help="Local file path of the PDF (e.g., document.pdf).")
    parser.add_argument("--force-extract", action="store_true", help="Force re-extraction of the PDF even if metadata exists.")
    args = parser.parse_args()

    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        logfire.error("GEMINI_API_KEY not set")
        raise ValueError("GEMINI_API_KEY not set in .env file.")

    try:
        # Initialize agents
        extraction_agent = PdfExtractionAgent(gemini_api_key)
        query_agent = PdfQueryAgent(gemini_api_key)

        # Check if PDF is already extracted and valid, unless forced
        if not args.force_extract and extraction_agent.is_pdf_extracted(args.pdf_path):
            logfire.info(f"PDF already extracted: {args.pdf_path}")
            print(f"\nPDF already extracted: {args.pdf_path}\n")
        else:
            # Extract PDF
            logfire.info(f"Attempting to extract PDF: {args.pdf_path}")
            print(f"\nAttempting to extract PDF: {args.pdf_path}\n")
            extraction_response = await extraction_agent.extract_pdf(args.pdf_path)
            print("\n--- PDF Extraction ---")
            print(extraction_response)

            if "Error" in extraction_response:
                return

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
            query_response = await query_agent.query_pdf(args.pdf_path, question)
            print(f"Answer: {query_response}\n")

    except Exception as e:
        logfire.error(f"Unexpected error: {str(e)}")
        

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        # Ensure event loop is properly closed
        loop = asyncio.get_event_loop()
        if not loop.is_closed():
            loop.close()