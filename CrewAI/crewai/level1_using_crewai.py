from crewai import Agent, Task, Crew, LLM
from dotenv import load_dotenv
import os
load_dotenv()
PERPLEXITY_API_KEY=os.getenv("PERPLEXITY_API_KEY")
# Initialize Large Language Model (LLM) of your choice (see all models on our Models page)
llm = LLM(
    model="llama-3.1-sonar-large-128k-online",
    api_key=PERPLEXITY_API_KEY,
    base_url="https://api.perplexity.ai/"
)



# Define the agent
agent = Agent(
    role='Answer Bot',
    goal='Explain technical concepts clearly',
    backstory='An expert AI educator who simplifies complex topics for beginners.',
    verbose=True,
    llm=llm
)

# Define the task
task = Task(
    description='Explain the four principles of Object-Oriented Programming (OOPS).',
    expected_output='A concise and beginner-friendly explanation of encapsulation, inheritance, abstraction, and polymorphism.',
    agent=agent
)

# Create the crew
crew = Crew(
    agents=[agent],
    tasks=[task],
    verbose=True
)

# Run the crew
result = crew.kickoff()
print("\n\n Final Result:\n", result)

