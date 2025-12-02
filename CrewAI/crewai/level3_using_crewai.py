from crewai import Agent, Task, Crew, Process, LLM
import os
from dotenv import load_dotenv

# Import both GoogleSerperAPIWrapper and GoogleSerperRun
from langchain_community.utilities import GoogleSerperAPIWrapper
from langchain_community.tools.google_serper.tool import GoogleSerperRun


load_dotenv()

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")



# --- Setup LLM (Perplexity) ---
llm = LLM(
    model="llama-3.1-sonar-large-128k-online",
    api_key=PERPLEXITY_API_KEY, # Use the variable, not the string literal
    base_url="https://api.perplexity.ai/"
)


from crewai_tools import (
    DirectoryReadTool,
    FileReadTool,
    SerperDevTool,
    WebsiteSearchTool
)

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

search_tool = SerperDevTool(api_key=SERPER_API_KEY)

user_input=input("")
search_agent = Agent(
    role="Web Analyst",
    goal="Search the internet and summarize recent and relevant results.",
    backstory="An expert at browsing and extracting meaningful insights from the internet.",
    verbose=True,
    allow_delegation=False,
    tools=[search_tool],
    llm=llm
)

# Define a task that uses the search tool
task = Task(
    description=user_input,
    expected_output="A concise summary of the most recent US tariff policies and related news.",
    agent=search_agent
)

# Create a Crew
crew = Crew(
    agents=[search_agent],
    tasks=[task],
    process=Process.sequential,
    verbose=True
)

# Execute the task
result = crew.kickoff()
print("\nFinal Result:\n", result)