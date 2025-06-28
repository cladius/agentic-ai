import os
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.google.gemini import Gemini
from agno.playground import Playground, serve_playground_app

# Load environment variables from .env file
load_dotenv()

# Set the Google API key for authentication
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Initialize a simple Agent using the Gemini model
gemini_agent = Agent(
    name="HelloWorld",
    model=Gemini(),
    markdown=True                # Enable Markdown formatting in responses
)

# Create a Playground app instance with the configured agent
app = Playground(agents=[gemini_agent]).get_app()

# Start the playground web app if this script is run directly
if __name__ == "__main__":
    serve_playground_app("l1:app", reload=True)