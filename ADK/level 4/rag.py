from google.auth import default
import vertexai
from vertexai.preview import rag
import os
from dotenv import load_dotenv
import logging
from google.api_core.exceptions import ServiceUnavailable, GoogleAPIError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")  # Default to us-central1
CORPUS_NAME = "my_first_corpus"
CORPUS_DESCRIPTION = "My first RAG corpus"

# Initialize Vertex AI
def initialize_vertex_ai():
    try:
        credentials, _ = default()
        vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=credentials)
        logger.info(f"Initialized Vertex AI with project: {PROJECT_ID}, location: {LOCATION}")
    except Exception as e:
        logger.error(f"Failed to initialize Vertex AI: {e}")
        raise

# Create a new corpus
def create_corpus():
    try:
        embedding_model_config = rag.EmbeddingModelConfig(
            publisher_model="publishers/google/models/text-embedding-004"
        )
        corpus = rag.create_corpus(
            display_name=CORPUS_NAME,
            description=CORPUS_DESCRIPTION,
            embedding_model_config=embedding_model_config,
        )
        logger.info(f"Created corpus: {corpus.name}")
        return corpus
    except ServiceUnavailable as e:
        logger.error(f"Service unavailable while creating corpus: {e}")
        raise
    except GoogleAPIError as e:
        logger.error(f"Google API error while creating corpus: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while creating corpus: {e}")
        raise

# Upload a local file to the corpus
def upload_file_to_corpus(corpus_name, file_path):
    try:
        if not os.path.isfile(file_path):
            raise ValueError(f"File not found: {file_path}")
        file_name = os.path.basename(file_path)
        rag_file = rag.upload_file(
            corpus_name=corpus_name,
            path=file_path,
            display_name=file_name,
            description=f"Uploaded {file_name}"
        )
        logger.info(f"Uploaded file: {file_name} to corpus")
        return rag_file  # Fixed: Removed invalid **kwargs
    except Exception as e:
        logger.error(f"Failed to upload file: {e}")
        raise

# Main function
def main():
    try:
        initialize_vertex_ai()
        corpus = create_corpus()
        file_path = "/Users/sakhiagrawal/Desktop/Project/bioengineering-10-00018.pdf"  # Update with a valid file path
        upload_file_to_corpus(corpus.name, file_path)
        logger.info("Process completed successfully")
    except Exception as e:
        logger.error(f"Main function failed: {e}")
        raise

if __name__ == "__main__":
    main()

    
    
