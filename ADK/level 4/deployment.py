from dotenv import load_dotenv
import os
import asyncio
import logging
from google.adk import Agent
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from vertexai.preview import rag
import vertexai
from vertexai import agent_engines
from prompts import return_instructions_root
MODEL_GEMINI_1_5_FLASH = "gemini-1.5-flash"
AGENT_MODEL = MODEL_GEMINI_1_5_FLASH

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


# Constants
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION")
STAGING_BUCKET = os.environ.get("STAGING_BUCKET")
APP_NAME = "rag_app"
MODEL_GEMINI_2_0_FLASH = "gemini-2.0-flash-001"
AGENT_MODEL = MODEL_GEMINI_2_0_FLASH

# Validate environment variables
for var in ["GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION", "STAGING_BUCKET", "GOOGLE_API_KEY", "RAG_CORPUS"]:
    if not os.getenv(var):
        raise ValueError(f"{var} environment variable not set.")

# Initialize Vertex AI
vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket=STAGING_BUCKET,
)

# Instantiate Vertex AI RAG Retrieval tool
ask_vertex_retrieval = VertexAiRagRetrieval(
    name="retrieve_rag_documentation",
    description="Use this tool to retrieve documentation and reference materials from the RAG corpus.",
    rag_resources=[
        rag.RagResource(
            rag_corpus=os.environ.get("RAG_CORPUS")
        )
    ],
    similarity_top_k=10,
    vector_distance_threshold=0.6,
)

# Define root agent
root_agent = Agent(
    name="ask_rag_agent",
    model=AGENT_MODEL,
    description="Agent to retrieve and answer queries using Vertex AI RAG corpus.",
    instruction=return_instructions_root(),
    tools=[ask_vertex_retrieval]
)

# Deploy the agent to Vertex AI Agent Engine
def deploy_agent():
    logger.info("Starting deployment of RAG agent to Vertex AI Agent Engine...")
    try:
        remote_app = agent_engines.create(
            agent_engine=root_agent,
            requirements=[
                "google-cloud-aiplatform[agent_engines,adk]",
                "google-cloud-storage",
                "python-dotenv",
                "cloudpickle==3.1.1",
                "pydantic==2.11.4",
                "llama-index"  # Added for files_retrieval
            ],
            gcs_dir_name="rag-agent-deployment",
            extra_packages=["prompts.py"]  # Include prompts.py
        )
        logger.info(f"Agent deployed successfully: {remote_app.name}")
        return remote_app
    except Exception as e:
        logger.error(f"Deployment failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Deploy the agent
    deployed_agent = deploy_agent()
    print(f"Deployed agent: {deployed_agent.name}")