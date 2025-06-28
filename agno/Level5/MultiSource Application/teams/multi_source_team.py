from agno.team import Team
from agno.models.google import Gemini
from agents.url_handler import create_url_handler_agent
from agents.json_corrector import create_json_corrector_agent
from agents.scraper import create_scraper_agent
from agents.pdf_processor import create_pdf_agent
from agents.youtube_processor import create_youtube_agent
from agents.web_processor import create_web_agent
from agents.text_processor import create_text_agent
from agents.mindmap_agent import create_mindmap_agent
from teams.podcast_team import create_podcast_team
from textwrap import dedent
from agents.podcast_agent import podcast_agent

# Create a multi-source processing team that handles various content types
# This team includes agents for URL handling, JSON correction, web scraping, PDF processing,
# YouTube video processing, web content processing, text processing, podcast handling, and mindmap creation.
# The team routes tasks based on the content type and provides instructions for each agent's role.
def create_multi_source_team(pdf_knowledge_base):
    url_handler = create_url_handler_agent()
    json_corrector = create_json_corrector_agent()
    scraper = create_scraper_agent()
    pdf_processor = create_pdf_agent(pdf_knowledge_base)
    youtube_processor = create_youtube_agent()
    web_processor = create_web_agent()
    text_processor = create_text_agent()
    podcastagent = podcast_agent()
    mindmap_processor = create_mindmap_agent()
    podcast_team = create_podcast_team()


    return Team(
        name="MultiSource Processor & Podcast Team",
        mode="route",
        model=Gemini(),
        show_members_responses=True,
        enable_agentic_context=True,
        show_tool_calls=True,
        monitoring=True,
        members=[
            url_handler,
            json_corrector,
            scraper,
            pdf_processor,
            youtube_processor,
            web_processor,
            text_processor,
            podcastagent,
            mindmap_processor,
            podcast_team,
        ],
        instructions=[
            dedent("""
            Route tasks:
            1. URL Handler extracts URLs.
            2. JSON Corrector fixes JSON.
            3. Route PDFs to PDF Processor, YouTube to YouTube Processor, webpages to Webpage Processor.
            4. Route text to Text Processor unless it's a podcast or mindmap request.
            5. Podcast requests (containing "podcast", "create podcast", "generate podcast", "make podcast") route to the agent podcast_agent.
            6. Mindmap requests (containing "mindmap", "create mindmap", "generate mindmap", "make mindmap") go to the agent named "mindmap-agent". If no such agent is found, return: "No Mindmap Agent available to handle the request."
            """)
        ]
    )