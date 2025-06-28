"""
Level 5 - Multi-Source Summarization and Podcast Generation Workflow
This module implements a multi-source summarization workflow that processes content from various sources such as 
PDFs, YouTube videos, webpages, and plain text. 
It also includes an optional feature to generate a podcast from the combined summary of these sources.
"""
import os
import re
import time
import base64
from uuid import uuid4
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
from agno.tools.youtube import YouTubeTools
from agno.agent import Agent, RunResponse
from agno.models.google import Gemini
from agno.tools.eleven_labs import ElevenLabsTools
from agno.tools.website import WebsiteTools
from agno.team import Team
from agno.workflow.workflow import Workflow
from agno.utils.audio import write_audio_to_file
from agno.utils.log import logger
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase, PDFUrlReader
from agno.vectordb.chroma import ChromaDb
from agno.embedder.google import GeminiEmbedder
from agno.playground import Playground, serve_playground_app
from openinference.instrumentation.agno import AgnoInstrumentor
from opentelemetry import trace as trace_api
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

# Load environment variables from .env file
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["ELEVEN_LABS_API_KEY"] = os.getenv("ELEVEN_LABS_API_KEY")
embedder = GeminiEmbedder(api_key=os.getenv("GOOGLE_API_KEY"))

# Set up Langfuse tracing
LANGFUSE_AUTH = base64.b64encode(
    f"{os.getenv('LANGFUSE_PUBLIC_KEY')}:{os.getenv('LANGFUSE_SECRET_KEY')}".encode()
).decode()
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://us.cloud.langfuse.com/api/public/otel"
os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {LANGFUSE_AUTH}"

# Configure the tracer provider
tracer_provider = TracerProvider()
tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))
trace_api.set_tracer_provider(tracer_provider=tracer_provider)

# Start instrumenting agno
AgnoInstrumentor().instrument()

def classify_url(url: str) -> str:
    """
    Classify a URL as 'pdf', 'youtube', or 'webpage'.
    
    Args:
        url (str): The URL to classify.
        
    Returns:
        str: The type of URL ('pdf', 'youtube', or 'webpage').
    """
    try:
        parsed_url = urlparse(url.lower())
        if not parsed_url.scheme or not parsed_url.netloc:
            logger.warning(f"Invalid URL format: {url}, treating as webpage")
            return 'webpage'
        if parsed_url.path.endswith('.pdf'):
            return 'pdf'
        if 'youtube.com' in parsed_url.netloc or 'youtu.be' in parsed_url.netloc:
            if '/watch' in parsed_url.path and 'v' in parse_qs(parsed_url.query):
                return 'youtube'
            if 'youtu.be' in parsed_url.netloc and parsed_url.path.strip('/'):
                return 'youtube'
        return 'webpage'
    except Exception as e:
        logger.warning(f"Error classifying URL {url}: {e}, treating as webpage")
        return 'webpage'


class MultiSourceWorkflow(Workflow):
    """
    A workflow that processes and summarizes content from multiple sources (PDFs, YouTube videos, webpages, and text)
    and optionally generates a podcast from the combined summary.

    Attributes:
        knowledge_base (PDFUrlKnowledgeBase): Shared knowledge base for PDF content processing.
        scraper_agent (Agent): Agent for scraping webpage content.
        pdf_agent (Agent): Agent for summarizing PDF content.
        youtube_agent (Agent): Agent for summarizing YouTube video transcripts.
        web_agent (Agent): Agent for summarizing webpage content.
        text_agent (Agent): Agent for summarizing plain text input.
        podcast_agent (Agent): Agent for generating podcast audio from summaries.
        team (Team): Team coordinating the agents.
    """

    knowledge_base = PDFUrlKnowledgeBase(    
        urls=[],   # URLs will be dynamically updated based on user input
        vector_db=ChromaDb(collection="pdf_content", embedder=embedder),
        embedder=embedder,
        reader=PDFUrlReader(),
    )
    
    # Scrape the content of the given URL and return the raw text.
    scraper_agent = Agent(
        name="Content Scraper",
        model=Gemini(),
        tools=[WebsiteTools()],
        instructions=[
            "Scrape the content of the given URL and return the raw text.",
            "Do not summarize or interpret the content, just return the scraped text.",
        ],
        debug_mode=True,
    )

    # Agent to summarize PDF content using the knowledge base
    pdf_agent = Agent(
        name="PDF Summarizer",
        model=Gemini(),
        knowledge=knowledge_base,
        search_knowledge=True,
        tools=[PDFUrlReader()],
        instructions=[
            "Query the knowledge base to retrieve the summarized content of the provided PDF URL.",
            "Summarize the retrieved content, focusing on key sections such as abstracts, introductions, conclusions, and key findings.",
            "Prioritize factual information, main arguments, or results, especially in academic, technical, or professional documents.",
            "If the content includes tables, charts, or references, extract key data points or insights rather than describing formatting.",
            "Produce a concise, informative summary of no more than 1500 characters, structured as 2-3 short paragraphs or bullet points for clarity.",
            "If the input is incomplete, noisy, or lacks clear sections, infer the main topic and summarize the most coherent parts, noting limitations (e.g., 'Summary based on partial content').",
            "Avoid including redundant details, filler text, or metadata (e.g., page numbers, headers)."
        ],
        debug_mode=True,
    )

    # Agent to summarize YouTube video transcripts or captions
    youtube_agent = Agent(
        name="YouTube Summarizer",
        model=Gemini(),
        tools=[YouTubeTools()],
        instructions=[
            "You are a YouTube agent. Obtain the captions of a YouTube video and give summary.",
            "Focus on key ideas, keep summary under 1500 characters.",
            "Summarize the video content based on the transcript, focusing on key ideas, main arguments, or central themes (e.g., tutorial steps, lecture points, story arcs).",
            "For conversational or fragmented transcripts, filter out filler words (e.g., 'um,' 'uh'), off-topic remarks, or repetitive phrases to highlight meaningful content.",
            "If no transcript is available (e.g., disabled or not found), return: 'No transcript available for {url}. Please provide the transcript manually or check if captions are enabled.'",
            "If the transcript is incomplete or noisy, summarize the coherent parts and note limitations (e.g., 'Summary based on partial transcript').",
            "Exclude metadata like timestamps or speaker labels unless they add critical context."
        ],
        debug_mode=True,
    )

    # Agent to summarize webpage content
    web_agent = Agent(
        name="Webpage Summarizer",
        model=Gemini(),
        instructions=[
            "Summarize the given webpage content.",
            "Keep summaries concise and to the point.",
            "Summarize the given webpage content, focusing on the main article, blog post, or primary information (e.g., product descriptions, news reports).",
            "Filter out noise from scraped content, such as advertisements, user comments, pop-ups, or unrelated links.",
            "For news articles, prioritize the headline, lead paragraph, and key facts; for blogs, focus on the main argument or narrative; for product pages, highlight features and benefits.",
            "Produce a concise summary of no more than 1500 characters, structured as 2-3 short paragraphs or bullet points for clarity.",
            "If the content is incomplete, ambiguous, or dominated by non-text elements (e.g., videos, images), summarize the available text and note limitations (e.g., 'Summary based on limited text content').",
            "If the input is irrelevant or empty, return: 'Unable to summarize {url} due to insufficient or irrelevant content.'"
        ],
        debug_mode=True,
    )

    # Agent to summarize plain text input
    text_agent = Agent(
        name="Text Summarizer",
        model=Gemini(),
        instructions=[
            "Summarize the given plain text input.",
            "Keep it concise and informative.",
            "Summarize the given plain text input, identifying and prioritizing the main ideas, arguments, or actionable points.",
            "For short texts (<100 words), provide a brief summary of 1-2 sentences; for longer texts, produce 2-3 short paragraphs or bullet points, not exceeding 1500 characters.",
            "If the text is unstructured or conversational, extract coherent themes or key messages, filtering out redundant or off-topic content.",
            "If the input is too short, trivial, or lacks substance, return: 'Input text is too short or lacks sufficient content for summarization.'",
            "Ensure the summary is concise, informative, and avoids reproducing verbatim phrases unless critical."
        ],
        debug_mode=True,
    )

    # Agent to generate podcast audio from summaries
    podcast_agent = Agent(
        name="Podcast Generator",
        model=Gemini(),
        tools=[
            ElevenLabsTools(
                api_key=os.getenv("ELEVEN_LABS_API_KEY"),
                voice_id="JBFqnCBsd6RMkjVDRZzb",
                model_id="eleven_multilingual_v2",
                target_directory="audio_generations",
            )
        ],
        instructions=[
            "Convert the given text into engaging spoken audio.",
            "Keep the audio natural and clear.",
            "Use the ElevenLabsTools to convert the summary to audio.",
            "You don't need to find the appropriate voice first, I already specified the voice to use.",
            "Ensure the summary is within the 2000 character limit to avoid ElevenLabs API limits.",
        ],
        debug_mode=True,
    )

    """
    A team of agents that processes and summarizes content from multiple sources (PDFs, YouTube videos, webpages, and text)
    and optionally generates a podcast from the combined summary.
    """
    team = Team(
        name="MultiSource Summarizer & Podcast Team",
        mode="coordinate",
        model=Gemini(),
        show_members_responses=True,    
        enable_agentic_context=True,
        share_member_interactions=True,
        show_tool_calls=True,
        monitoring=True,
        members=[scraper_agent, pdf_agent, youtube_agent, web_agent, text_agent, podcast_agent],
    )

    def __init__(self, *args, **kwargs):
        """ Initialize the MultiSourceWorkflow with team configuration and logging. """
        super().__init__(*args, **kwargs)
        # Log team configuration
        logger.info(f"Team Configuration - Name: {self.team.name}, Mode: {self.team.mode}, "
                    f"Show Members Responses: {self.team.show_members_responses}, "
                    f"Enable Agentic Context: {self.team.enable_agentic_context}, "
                    f"Share Member Interactions: {self.team.share_member_interactions}, "
                    f"Show Tool Calls: {self.team.show_tool_calls}")

    
    def run(self, prompt: str) -> RunResponse:
        """
        Executes the multi-source summarization workflow based on the provided prompt.
        Args:
            prompt (str): The user input containing URLs, text, or both to be summarized.

        Returns:
            RunResponse: A RunResponse object containing the summary and optionally podcast audio.
        Behavior:
            The workflow will attempt to extract URLs and text from the prompt, classify the URLs, and then process each type of content using the appropriate agent. If podcast generation is requested, it will also generate audio from the summary.
        
        """
        # Url extraction and classification
        url_pattern = r'(?:https?://|www\.)[^\s<>"]+|[^\s<>"]+\.(?:com|org|net|edu|gov|io)[^\s<>"]*'
        urls = re.findall(url_pattern, prompt)
        logger.info(f"Extracted URLs from prompt: {urls}")

        # Remove URLs from the prompt to get the remaining text
        remaining_text = re.sub(url_pattern, '', prompt).strip()
        logger.info(f"Remaining text after removing URLs: {remaining_text}")

        pdf_urls = []
        youtube_urls = []
        web_urls = []

        # Normalize URLs and classify them
        for url in urls:
            # Normalize URL: add https:// if no scheme is present
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            url_type = classify_url(url)
            if url_type == 'pdf':
                pdf_urls.append(url)
            elif url_type == 'youtube':
                youtube_urls.append(url)
            else:
                web_urls.append(url)

        logger.info(f"Classified URLs - PDFs: {pdf_urls}, YouTube: {youtube_urls}, Webpages: {web_urls}")

        summaries = []
        warnings = []  # To store warnings for failed summarizations

        # Helper function to scrape content with retries and exponential backoff
        def attempt_scraping(url, max_retries=3):
            """
            Attempts to scrape the content of a given URL with retries and exponential backoff.
            Args:
                url (str): The URL to scrape.
                max_retries (int): The maximum number of retry attempts.
            Returns:
                str: The scraped content if successful, None otherwise.
            Raises:
                Exception: If all attempts fail, an exception is raised with a warning message.
            """
            for attempt in range(max_retries):
                try:
                    # Scrape the content using the scraper agent
                    response: RunResponse = self.scraper_agent.run(f"Scrape the content of this URL: {url}")
                    if response and response.content and "I don't have enough information" not in response.content.lower():
                        # Log a preview of the scraped content (first 200 characters)
                        preview = response.content[:200] + ("..." if len(response.content) > 200 else "")
                        logger.info(f"Scraped content preview for {url}: {preview}")
                        return response.content
                    else:
                        logger.warning(f"Attempt {attempt + 1}/{max_retries} failed to scrape {url}: {response.content if response else 'No response'}")
                except Exception as e:
                    # Log the exception and retry
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed to scrape {url} with error: {e}")
                if attempt < max_retries - 1:
                    # Exponential backoff: wait 2^attempt seconds before retrying
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying scraping for {url} after {wait_time} seconds...")
                    time.sleep(wait_time)
            warnings.append(f"Failed to scrape {url} after {max_retries} attempts. The service may be temporarily unavailable.")
            return None

        # Helper function to summarize content with retries
        def attempt_summarization(agent, instruction, content, url, max_retries=2):
            """
            Attempts to summarize the given content using the specified agent with retries.
            Args:
                agent (Agent): The agent to use for summarization.
                instruction (str): The instruction to provide to the agent.
                content (str): The content to summarize.
                url (str): The URL associated with the content, for logging purposes.
                max_retries (int): The maximum number of retry attempts.
            Returns:
                str: The summary content if successful, or a warning message if all attempts fail.
            Raises:
                Exception: If all attempts fail, an exception is raised with a warning message.
            """
            for attempt in range(max_retries):
                try:
                    # Run the agent with the provided instruction and content
                    response: RunResponse = agent.run(instruction.format(content=content))
                    if response and response.content and "I don't have enough information" not in response.content.lower():
                        return response.content
                    else:
                        logger.warning(f"Attempt {attempt + 1}/{max_retries} failed to summarize for {url}: {response.content if response else 'No response'}")
                except Exception as e:
                    # Log the exception and retry
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed to summarize for {url} with error: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying summarization for {url}...")
            warnings.append(f"Failed to summarize content from {url} after {max_retries} attempts.")
            return f"[Unable to summarize {url} due to processing issues.]"

        # Process each type of URL and summarize content
        for url in pdf_urls:
            # Scrape PDF content
            logger.info(f"Scraping PDF content: {url}")
            PDFUrlKnowledgeBase.urls = [url]  # Update knowledge base with the current URL
            self.knowledge_base.urls = PDFUrlKnowledgeBase.urls  # Update knowledge base with new URL
            self.knowledge_base.load(recreate=False)  # Load the knowledge base with the new URL
            logger.info(f"Summarizing PDF content from: {url}")
            summary = attempt_summarization(self.pdf_agent,f"Query the knowledge base to retrieve the content of the PDF at {url} and summarize it.", None, url)
            logger.info(f"PDF summary: {summary}")
            summaries.append(summary)
            
        # Process YouTube URLs
        for url in youtube_urls:
            logger.info(f"Scraping YouTube content: {url}")
            logger.info(f"Summarizing YouTube content from: {url}")
            summary = attempt_summarization(self.youtube_agent, f"Obtain the captions of the YouTube video at {url} and summarize the content.", None, url)
            logger.info(f"YouTube summary: {summary}")
            summaries.append(summary)
        
        # Process Webpage URLs
        for url in web_urls:
            logger.info(f"Scraping Webpage content: {url}")
            scraped_content = attempt_scraping(url) 
            if scraped_content:
                logger.info(f"Summarizing Webpage content from: {url}")
                summary = attempt_summarization(self.web_agent, "Summarize the given webpage content: {content}", scraped_content, url)
                logger.info(f"Webpage summary: {summary}")
                summaries.append(summary)
            else:
                summaries.append(f"[Unable to summarize {url} due to scraping issues. Please try again later or provide the content directly.]")

        # Process remaining text input
        trivial_keywords = {"summarize", "summary", "give", "provide", "create", "generate","and", "of", "for", "to", "with"} # Set of trivial keywords to ignore
        # Check if remaining text is not trivial and has enough content
        if (remaining_text and len(remaining_text.split()) > 3 and 
            not all(word.lower() in trivial_keywords for word in remaining_text.split())):
            logger.info("Summarizing remaining text from prompt")
            response: RunResponse = self.text_agent.run(f"Summarize this text: {remaining_text}")
            if response and response.content and "I don't have enough information" not in response.content.lower():
                logger.info(f"Text summary: {response.content}")
                summaries.append(response.content)
            else:
                logger.warning(f"Failed to summarize remaining text: {response.content if response else 'No response'}")
                warnings.append("Failed to summarize the provided text.")
        else:
            logger.info("Skipping summarization of remaining text as it is trivial or too short.")

        # Combine all summaries into a single response
        combined_summary = "\n\n".join(summaries).strip()
        logger.info(f"Combined summary: {combined_summary}")

        if not combined_summary:
            run_response = RunResponse(content="No content provided to summarize.", audio=None)
        else:
            run_response = RunResponse(content=combined_summary, audio=None)

        # Initialize metadata safely
        run_response.metadata = getattr(run_response, 'metadata', {})
        
        # Add warnings to metadata if any scraping or summarization failed
        if warnings:
            run_response.metadata["warnings"] = warnings

        # Initialize podcast keywords
        podcast_keywords = ["podcast","create podcast","generate podcast","podcast generation","make podcast","podcast summary"]
        # Check podcast keywords only in remaining_text, not in URLs, using whole-word matching
        words = re.findall(r'\b\w+\b', remaining_text.lower())  # Split into words
        podcast_requested = any(keyword in words for keyword in podcast_keywords)
        logger.debug(f"Podcast keywords check: {podcast_keywords}, Words in remaining_text: {words}, Podcast requested: {podcast_requested}")

        # Check if podcast generation is requested
        if podcast_requested and combined_summary:
            logger.info("User requested podcast generation, creating audio...")
            summary_length = len(combined_summary)
            logger.debug(f"Summary length for podcast: {summary_length} characters")
            if summary_length > 2000:
                combined_summary = combined_summary[:1997] + "..."
                logger.warning("Summary truncated to 2000 characters for ElevenLabs API compatibility.")
            
            # Run the podcast agent with the combined summary
            logger.debug(f"Input to podcast agent: {combined_summary}") 
            podcast_response: RunResponse = self.podcast_agent.run(combined_summary)
            logger.info(f"Podcast generation response: audio={'present' if podcast_response.audio else 'not present'}")
            if podcast_response.audio:
                logger.debug(f"Podcast audio details: {podcast_response.audio}")
            else:
                logger.debug("No audio returned by podcast agent.")
            # If podcast audio is generated, save it to a file
            if podcast_response.audio and len(podcast_response.audio) > 0:
                os.makedirs("audio_generations", exist_ok=True)
                filename = f"audio_generations/podcast_{uuid4()}.wav"
                try:
                    write_audio_to_file(
                        audio=podcast_response.audio[0].base64_audio,
                        filename=filename,
                    )
                    run_response.audio = podcast_response.audio
                    run_response.metadata["podcast_file"] = filename
                    logger.info(f"Podcast audio saved at: {filename}")
                except Exception as e:
                    logger.error(f"Failed to save podcast audio: {e}")
                    warnings.append(f"Failed to save podcast audio: {str(e)}")
            else:
                logger.warning("Podcast generation returned no audio.")
                warnings.append("Podcast generation failed to produce audio.")
        else:
            logger.info("Podcast generation not requested or no summary available.")

        # Update warnings in metadata after podcast generation
        if warnings:
            run_response.metadata["warnings"] = warnings

        return run_response

# Instantiate the workflow
multi_source_workflow = MultiSourceWorkflow(
    name="Multi-Source Summarizer with Optional Podcast",
    workflow_id="multi_source_summary_podcast",
    monitoring=True,  
)

# Playground integration
app = Playground(workflows=[multi_source_workflow]).get_app()

if __name__ == "__main__":
    """ Entrypoint for starting the Agno Playground app with MultiSourceWorkflow. """
    logger.info("Starting Agno playground with MultiSourceWorkflow...")
    serve_playground_app("l5-1:app")