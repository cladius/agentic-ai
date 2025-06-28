from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.website import WebsiteTools

# Create the Content Scraper Agent
# This agent is designed to scrape content from a given URL and return the raw text.
# It uses the WebsiteTools to fetch and process the webpage content.
# The agent is configured to handle errors gracefully and return a specific message if scraping fails.
def create_scraper_agent():
    return Agent(
        name="Content Scraper",
        model=Gemini(),
        tools=[WebsiteTools()],
        instructions=[
            "Scrape the content of the given URL and return the raw text.",
            "If error, return: 'Failed to process webpage content: {content}'."
        ],
        debug_mode=True,
    )