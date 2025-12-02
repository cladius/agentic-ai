from crewai import Agent, Task, Crew, LLM
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.memory import VectorStoreRetrieverMemory
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# Use HuggingFace embeddings instead of OpenAI
embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = Chroma(collection_name="career_guidance", embedding_function=embedding)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
memory = VectorStoreRetrieverMemory(retriever=retriever)

# Initialize Perplexity LLM
llm = LLM(
    model="llama-3.1-sonar-large-128k-online",
    api_key=PERPLEXITY_API_KEY,
    base_url="https://api.perplexity.ai/"
)

# Define agent
conversational_agent = Agent(
    role='Career Guide Bot',
    goal='Offer personalized academic and career guidance',
    backstory='An AI assistant for students, helping them explore tailored career and learning paths.',
    verbose=True,
    llm=llm,
    memory=memory
)

task1 = Task(
    description="User is Sumedh, an engineering student interested in compiler design and ML. Suggest career options.",
    expected_output="Relevant career paths or fields aligned with the user's interests in compiler design and machine learning.",
    agent=conversational_agent
)

task2 = Task(
    description="User wants to know about relevant textbooks based on their previous interests.",
    expected_output="Suggestions for textbooks or learning resources suited to the user's background and interests.",
    agent=conversational_agent,
    context=[task1]
)


# Create and run the crew
crew = Crew(
    agents=[conversational_agent],
    tasks=[task1, task2],
    verbose=True
)

if __name__ == "__main__":
    result = crew.kickoff()
    print("\n\n Final Result:\n", result)
