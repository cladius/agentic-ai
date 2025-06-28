from agno.agent import Agent
from agno.models.google import Gemini
from textwrap import dedent

# Create the JSON Corrector agent
# This agent is designed to correct malformed JSON output from the URL Handler agent.
# It ensures the output matches a specific structure and handles various cases of malformed JSON.   
def create_json_corrector_agent():
    return Agent(
        agent_id="json-corrector",
        name="JSON Corrector",
        model=Gemini(),
        instructions=[
            dedent("""
            You are a JSON correction agent. Your task is to fix malformed JSON output from the URL Handler agent and return a valid JSON string matching:

            {"pdf_urls":[],"youtube_urls":[],"web_urls":[],"remaining_text":"string","errors":"array"}

            Steps:
            1. Receive the URL Handler's output.
            2. If valid JSON and matches the structure, return it unchanged.
            3. If wrapped in Markdown (e.g., ```json ... ```), strip Markdown and validate.
            4. If malformed (e.g., unclosed brackets, nested objects), fix by:
               - Closing unclosed brackets or quotes.
               - Removing nested objects, keeping the first valid set of "pdf_urls", "youtube_urls", etc.
               - Ensuring all fields are present with default values if missing.
            5. If correction fails, return:
            {"pdf_urls":[],"youtube_urls":[],"web_urls":[],"remaining_text":"","errors":["Failed to correct JSON"]}

            CRITICAL:
            - Output ONLY a valid JSON string.
            - NO Markdown (e.g., ```json ... ```), comments, or explanations.
            - Ensure proper bracket and quote closure.
            - If no URLs are found, pass the valid JSON unchanged.

            Examples:
            Input: ```json\n{"pdf_urls":["https://example.com/doc.pdf"],"youtube_urls":[],"web_urls":[],"remaining_text":"summarize","errors":[]}\n```
            Output: {"pdf_urls":["https://example.com/doc.pdf"],"youtube_urls":[],"web_urls":[],"remaining_text":"summarize","errors":[]}

            Input: invalid
            Output: {"pdf_urls":[],"youtube_urls":[],"web_urls":[],"remaining_text":"","errors":["Failed to correct JSON"]}
            """)
        ],
        debug_mode=True,
    )