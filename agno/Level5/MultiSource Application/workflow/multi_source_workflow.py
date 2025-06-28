import os
import json
import sqlite3
from datetime import datetime, timedelta
from agno.workflow.workflow import Workflow
from agno.utils.log import logger
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase, PDFUrlReader
from agno.vectordb.chroma import ChromaDb
from agno.embedder.google import GeminiEmbedder
from teams.multi_source_team import create_multi_source_team
from agno.agent import RunResponse

# This module defines a multi-source workflow that processes various content types,
# including PDFs, YouTube videos, web pages, and text. It initializes knowledge bases,  
# creates a team of agents, and manages a SQLite cache for responses.


class MultiSourceWorkflow(Workflow):
    def _initialize_knowledge_base(self, agent_name: str, collection_name: str, urls: list = None):
        """Initialize the knowledge base for the specified agent."""
        try:
            vector_db = ChromaDb(collection=collection_name, embedder=self.embedder)
            vector_db.client.get_or_create_collection(collection_name)
            if agent_name == "pdf_agent":
                return PDFUrlKnowledgeBase(
                    urls=urls or [],
                    vector_db=vector_db,
                    embedder=self.embedder,
                    reader=PDFUrlReader(),
                )
            else:
                raise ValueError(f"Invalid agent_name: {agent_name}")
        except Exception as e:
            logger.error(f"Failed to initialize knowledge base for {agent_name}: {str(e)}")
            raise RuntimeError(f"Knowledge base initialization failed: {str(e)}")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.embedder = GeminiEmbedder(api_key=os.getenv("GOOGLE_API_KEY"))

        # Initialize knowledge bases
        self.pdf_knowledge_base = self._initialize_knowledge_base(
            agent_name="pdf_agent",
            collection_name="pdf_content",
        )

        # Create team
        self.team = create_multi_source_team(self.pdf_knowledge_base)
        self.podcast_conversation_team = self.team.members[-1]  # Podcast team is the last member
        self.mindmap_agent = self.team.members[-2]  # Mindmap agent is the second-to-last member

        # Initialize SQLite cache (inspired by agno's SqliteStorage)
        self.db_file = "tmp/workflow_cache.db"
        self.table_name = "workflow_cache"
        self.init_cache()

        logger.info(f"Team Configuration - Name: {self.team.name}, Mode: {self.team.mode}")

    def init_cache(self):
        """Initialize the SQLite cache database, following agno's SqliteStorage approach."""
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)

        # Connect to the SQLite database
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # Create the cache table if it doesn't exist
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                prompt TEXT PRIMARY KEY,
                response TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Enable Write-Ahead Logging for better concurrency
        cursor.execute("PRAGMA journal_mode=WAL")

        conn.commit()
        conn.close()
        logger.info(f"Initialized SQLite cache at {self.db_file} with table {self.table_name}")

    def get_cached_response(self, prompt: str) -> RunResponse:
        """Retrieve a cached response for the given prompt."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(f"SELECT response FROM {self.table_name} WHERE prompt = ?", (prompt,))
        result = cursor.fetchone()
        conn.close()
        if result:
            logger.info(f"Cache hit for prompt: {prompt}")
            response_dict = json.loads(result[0])
            response = RunResponse(**response_dict)
            # Check if associated files exist (e.g., mindmap or audio)
            if response.audio and not os.path.exists(response.audio):
                logger.warning(f"Audio file {response.audio} not found; treating as cache miss")
                return None
            # For mindmap, check if the file exists (based on content message)
            if "mindmap_output.png" in response.content and not os.path.exists("mindmap_output.png"):
                logger.warning("Mindmap file mindmap_output.png not found; treating as cache miss")
                return None
            return response
        logger.info(f"Cache miss for prompt: {prompt}")
        return None

    def save_to_cache(self, prompt: str, response: RunResponse):
        """Save a response to the cache."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            f"INSERT OR REPLACE INTO {self.table_name} (prompt, response) VALUES (?, ?)",
            (prompt, json.dumps(response.to_dict()))
        )
        conn.commit()
        conn.close()
        logger.debug(f"Saved response to cache for prompt: {prompt}")

    def evict_old_entries(self):
        """Evict cache entries older than 7 days."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        expiration_date = datetime.now() - timedelta(days=7)
        cursor.execute(f"DELETE FROM {self.table_name} WHERE timestamp < ?", (expiration_date,))
        conn.commit()
        conn.close()
        logger.debug("Evicted old cache entries")

    def run(self, prompt: str) -> RunResponse:
        '''Run the multi-source workflow with the given prompt.
        This method processes the prompt through a series of agents, handling URLs, PDFs, YouTube videos,
        web pages, and text. It also manages caching and error handling.
        Args:
            prompt (str): The input prompt containing URLs or text to be processed.
            Returns:
            RunResponse: The final response containing processed content, warnings, and any associated audio.
    '''
        warnings = []
        run_response = RunResponse(content="", audio=None)

        # Check cache first
        cached_response = self.get_cached_response(prompt)
        if cached_response:
            return cached_response

        # Step 1: Route to URL Handler and correct with JSON Corrector
        max_retries = 2
        for attempt in range(max_retries + 1):
            url_response = self.team.members[0].run(prompt)  # URL Handler
            if not url_response or not url_response.content:
                warnings.append(f"Attempt {attempt + 1}: Failed to process URLs: No response from URL Handler.")
                if attempt < max_retries:
                    continue
                run_response.content = f"Failed to process input after {max_retries + 1} attempts. Warnings: {warnings}"
                self.save_to_cache(prompt, run_response)
                return run_response

            logger.debug(f"Attempt {attempt + 1}: Raw URL Handler response: {json.dumps(url_response.content, ensure_ascii=False)}")

            corrector_response = self.team.members[1].run(url_response.content)  # JSON Corrector
            logger.debug(f"Attempt {attempt + 1}: JSON Corrector response: {json.dumps(corrector_response.content, ensure_ascii=False)}")

            corrected_content = corrector_response.content
            if corrected_content.startswith("```json\n") and corrected_content.endswith("\n```"):
                corrected_content = corrected_content[8:-4].strip()

            try:
                corrected_data = json.loads(corrected_content)
                if not isinstance(corrected_data, dict) or any(key not in corrected_data for key in ["pdf_urls", "youtube_urls", "web_urls", "remaining_text", "errors"]):
                    raise ValueError("Invalid JSON structure")
                pdf_urls = corrected_data.get('pdf_urls', [])
                youtube_urls = corrected_data.get('youtube_urls', [])
                web_urls = corrected_data.get('web_urls', [])
                remaining_text = corrected_data.get('remaining_text', prompt)
                errors = corrected_data.get('errors', [])
                if errors:
                    warnings.extend(errors)
                break
            except (json.JSONDecodeError, ValueError) as e:
                warnings.append(f"Attempt {attempt + 1}: Invalid JSON from JSON Corrector: {str(e)}")
                if attempt < max_retries:
                    continue
                run_response.content = f"Failed to process input after {max_retries + 1} attempts due to invalid JSON. Warnings: {warnings}"
                self.save_to_cache(prompt, run_response)
                return run_response

        # Step 2: Update knowledge bases with URLs and load
        if pdf_urls:
            try:
                self.pdf_knowledge_base.urls = pdf_urls
                self.pdf_knowledge_base.load(recreate=False)
            except Exception as e:
                warnings.append(f"Failed to load PDF URLs: {str(e)}")

        # Step 3: Process URLs and text via team routing
        responses = []
        if pdf_urls or youtube_urls or web_urls or remaining_text:
            task_input = {
                "pdf_urls": pdf_urls,
                "youtube_urls": youtube_urls,
                "web_urls": web_urls,
                "remaining_text": remaining_text
            }
            task_instruction = (
                f"Process content: {json.dumps(task_input)}. "
                f"Route PDFs to PDF Processor, YouTube to YouTube Processor, webpages to Webpage Processor. "
                f"Route text to Text Processor unless it’s a podcast or mindmap request."
            )
            logger.debug(f"Routing task: {task_instruction}")
            response = self.team.run(task_instruction, stream_intermediate_steps=True)
            responses.append(response.content)
        else:
            warnings.append("No valid content provided for processing.")

        # Step 4: Combine responses
        combined_response = "\n\n".join([r.strip() for r in responses if r.strip()])
        if not combined_response:
            run_response.content = f"No content processed. Warnings: {warnings}"
        else:
            run_response.content = combined_response

        if warnings:
            logger.warning(f"\n\nWarnings: {warnings}")

        # Save to cache before returning
        self.save_to_cache(prompt, run_response)

        # Periodically evict old entries (e.g., every run)
        self.evict_old_entries()

        return run_response