from vertexai import agent_engines
import vertexai
import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION")
AGENT_ENGINE_ID = os.environ.get("AGENT_ENGINE_ID")

vertexai.init(project=PROJECT_ID, location=LOCATION)
remote_agent = agent_engines.ReasoningEngine(
    f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{AGENT_ENGINE_ID}"
)
response = remote_agent.query(
    input="What is the latest documentation on Vertex AI RAG?",
    config={"configurable": {"session_id": "1010"}}
)
print("Agent Response:", response)