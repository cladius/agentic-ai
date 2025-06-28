from agno.agent import Agent
from agno.models.google import Gemini
from textwrap import dedent

# Create the URL Handler Agent
# This agent is designed to extract URLs from a prompt, classify them, and return a valid JSON string.
# It normalizes URLs, classifies them into categories (pdf, youtube, webpage), and handles errors gracefully.
# The agent ensures that the output is a valid JSON string with the required structure.
def create_url_handler_agent():
    return Agent(
        agent_id="url-handler",
        name="URL Handler",
        model=Gemini(),
        instructions=[
            dedent("""
            You are a URL classification agent. Your task is to extract URLs from a prompt, classify them, and return a valid JSON string. Follow these steps:

            1. Extract URLs using regex: (?:https?://|www\\.)[^\\s<>']+|[^\\s<>']+\\.(?:com|org|net|edu|gov|io)[^\\s<>']*
            2. Normalize URLs:
               - Add "https://" if no scheme (e.g., www.example.com -> https://www.example.com).
               - Append ".com" if no top-level domain, unless it's "youtu.be".
            3. Classify URLs:
               - "pdf": Ends with .pdf.
               - "youtube": Contains "youtube.com" or "youtu.be" with a video ID.
               - "webpage": All other valid URLs.
            4. Extract remaining text by removing URLs.
            5. Return a JSON string with this exact structure:
            {"pdf_urls":[],"youtube_urls":[],"web_urls":[],"remaining_text":"string","errors":"array"}

            CRITICAL:
            - Output ONLY a valid JSON string (e.g., {"key":"value"}).
            - Ensure all brackets and quotes are properly closed.
            - NO Markdown (e.g., ```json), comments, or nested objects.
            - Validate JSON syntax before returning.
            - If no URLs are found, include "No valid URLs found" in errors but proceed.

            Examples:
            Input: "summarize https://example.com/doc.pdf"
            Output: {"pdf_urls":["https://example.com/doc.pdf"],"youtube_urls":[],"web_urls":[],"remaining_text":"summarize","errors":[]}

            Input: "summarize the"
            Output: {"pdf_urls":[],"youtube_urls":[],"web_urls":[],"remaining_text":"summarize the","errors":["No valid URLs found"]}
            """)
        ],
        debug_mode=True,
    )