from langchain_community.tools.tavily_search import TavilySearchResults 
from langchain_groq import ChatGroq 
import os 
from dotenv import load_dotenv 

# Optional: Load environment variables 
# from .env load_dotenv() 
#TAVILY_API_KEY = os.getenv("TAVILY_API_KEY") 

# # Step 1: Initialize Groq model 
llm=ChatGroq(groq_api_key="Your API KEY",model="llama-3.3-70b-versatile") 

# Step 2: Initialize Tavily search tool 
search_tool = TavilySearchResults(k=3) 

# Step 3: Manual message format 
from langchain.agents import initialize_agent, AgentType 
agent = initialize_agent(tools=[search_tool],llm=llm,agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,verbose=True,handle_parsing_errors=True, 
                         agent_kwargs={"prefix": "You are an assistant that must always use tools to find the correct answer, never guess.",}) 

# Step 4: Ask question 
response = agent.run("What is the latest news about AI regulations in the EU?") 
print("\nAgent Response:\n", response) 