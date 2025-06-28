import os
from dotenv import load_dotenv
from typing import List
from agno.agent import Agent
from agno.models.google import Gemini
from agno.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.eval.accuracy import AccuracyEval
from agno.playground import Playground, serve_playground_app

# Load environment variables from .env file
load_dotenv()
# Set the Google API key for authentication
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Agent to reformulate user queries for better search effectiveness
query_reformulator = Agent(
    name="Query Reformulator Agent",
    model=Gemini(),
    role="Reformulates user queries to be more effective for searching.",
    instructions=[
        "You will be given a user query.",
        "Reformulate the query to be more effective for searching.",
        "Return the reformulated query as a string."
    ],
)

# Agent to search the web using DuckDuckGo tools
web_searcher = Agent(
    name="Web Searcher Agent",
    model=Gemini(),
    role="Searches the web for information on a topic",
    tools=[DuckDuckGoTools()],
    instructions=[
        "You will be given a reformulated query.", 
        "Search the web for information related to this query.",
        "Return a list of relevant articles with their titles, URLs, and summaries.",
    ],
    add_datetime_to_instructions=True,
)

# Agent to synthesize answers from multiple articles
ans_synthesis_agent = Agent(
    name="Answer Synthesis Agent",
    model=Gemini(),
    role="Synthesizes answers from multiple sources",
    instructions=[
        "You will be given a list of articles.",
        "Synthesize the information from these articles into a coherent answer.",
        "Make sure to include key points from each article.",
        "Use the titles and summaries to guide your synthesis.",
        "Return the synthesized answer as a string."
    ],
)

# Define a team of agents to coordinate the web search and answer synthesis process
web_searcher_team = Team(
    name="Web Searcher Team",
    mode="coordinate",  # Team members work in a coordinated sequence
    model=Gemini(id="gemini-1.5-flash"),
    members=[query_reformulator, web_searcher, ans_synthesis_agent],
    instructions=[
        "First, reformulate the user query to be more effective for searching.",
        "Then, search the web for information related to the reformulated query.",
        "Finally, synthesize the information from the articles into a coherent answer.",
    ],
    show_tool_calls=True,           # Show tool usage in output
    markdown=True,                  # Format output as Markdown
    debug_mode=True,                # Enable debug mode for more details
    show_members_responses=True,    # Show responses from all team members
    enable_agentic_context=True,    # Allow agents to use their own context
    enable_team_history=True,       # Enable team conversation history
    num_of_interactions_from_history=5,  # Number of past interactions to include
    share_member_interactions=True, # Share interactions among team members
    monitoring=True,            # Enable monitoring of team interactions
)

evaluation = AccuracyEval(
    name="Web Searcher Team Evaluation",
    model=Gemini(),
    team=web_searcher_team,
    input="What are the latest developments in artificial intelligence in 2024?",
    expected_output="A comprehensive summary covering recent AI developments in 2024, including advancements in large language models, AI safety research, new AI applications, and major industry announcements. The response should synthesize information from multiple sources and provide specific examples.",
)

result = evaluation.run(print_results=True)
# Create a Playground app instance with the configured team
app = Playground(teams=[web_searcher_team]).get_app()

# Start the playground web app if this script is run directly
if __name__ == "__main__":
    serve_playground_app("web-teams:app")