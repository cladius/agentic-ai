import os
from dotenv import load_dotenv
from agno.utils.log import logger
from agno.playground import Playground, serve_playground_app
from workflow.multi_source_workflow import MultiSourceWorkflow, PDFUrlReader

# Load environment variables
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["ELEVEN_LABS_API_KEY"] = os.getenv("ELEVEN_LABS_API_KEY")

PDFUrlReader.separators = ["\n\n", "\n", ".", " "]

# Instantiate the workflow
multi_source_workflow = MultiSourceWorkflow(
    name="Multi-Source Processor with Podcast",
    workflow_id="multi_source_processor_podcast",
    monitoring=True,
)

# Playground integration
app = Playground(workflows=[multi_source_workflow]).get_app()

if __name__ == "__main__":
    logger.info("Starting Agno playground with MultiSourceWorkflow...")
    serve_playground_app("main:app")