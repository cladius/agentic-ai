import os
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google.gemini import Gemini
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.playground import Playground, serve_playground_app

# Load environment variables from .env file
load_dotenv()
# Set the Google API key for authentication
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Create an Agent instance configured for web search tasks.
agent = Agent(
    name="WebSearchAgent",
    model=Gemini(),                 # - Uses the Gemini model for language processing.
    tools=[DuckDuckGoTools()],      # - Integrates DuckDuckGo tools for web search capabilities.
    show_tool_calls=True,           # Show tool usage in output
    markdown=True,                  # Format output as Markdown
    stream=True,                    # Enable streaming responses
    monitoring=True,                # Enable monitoring for debugging
    stream_intermediate_steps=True, # Stream intermediate reasoning steps
)

# Create a Playground app instance with the configured agent
app = Playground(agents=[agent]).get_app()

# Start the playground web app if this script is run directly
if __name__ == "__main__":
    serve_playground_app("websearch:app")