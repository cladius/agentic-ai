import logging
import hashlib
from typing import List, Dict, Any, Optional
import chromadb
from google.adk.agents import LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Try relative imports first (for local development), then absolute imports (for ADK)
try:
    from constants_and_models import APP_NAME, USER_ID, SESSION_ID
except ImportError:
    from level5.constants_and_models import APP_NAME, USER_ID, SESSION_ID

logger = logging.getLogger(__name__)



"""This module provides a manager for ChromaDB integration, allowing storage, retrieval, and processing of documents."""
# --- ChromaDB Integration ---
class ChromaDBManager:
    def __init__(self, podcast_agent=None, text_agent=None, image_generation_agent=None, session_service=None):
        self.client = chromadb.Client()
        try:
            self.collection = self.client.get_collection(name="link_data")
        except Exception as e:
            # Handle different ChromaDB versions - try to create collection if it doesn't exist
            if "does not exist" in str(e) or "not found" in str(e).lower():
                self.collection = self.client.create_collection(name="link_data")
            else:
                raise e
        self.podcast_agent = podcast_agent
        self.text_agent = text_agent
        self.image_generation_agent = image_generation_agent
        self.session_service = session_service

    """This class manages the ChromaDB collection for storing and retrieving documents."""
    def store_document(self, url: str, content: str, content_type: str = "text") -> str:
        doc_id = hashlib.md5(url.encode()).hexdigest()
        try:
            # Check if document already exists
            existing = self.collection.get(ids=[doc_id])
            if existing and existing["ids"]:
                # Update existing document
                self.collection.update(
                    documents=[content],
                    metadatas=[{"url": url, "content_type": content_type}],
                    ids=[doc_id]
                )
            else:
                # Add new document
                self.collection.add(
                    documents=[content],
                    metadatas=[{"url": url, "content_type": content_type}],
                    ids=[doc_id]
                )
        except Exception as e:
            logger.error(f"Error storing document: {str(e)}")
            # Try to add as new document if update fails
            self.collection.add(
                documents=[content],
                metadatas=[{"url": url, "content_type": content_type}],
                ids=[doc_id]
            )
        return doc_id
    
    
    
    """Stores a document in the ChromaDB collection with a unique ID based on the URL."""
    def search_similar(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return [
            {
                "id": id,
                "content": doc,
                "url": meta["url"],
                "content_type": meta["content_type"]
            }
            for id, doc, meta in zip(results["ids"][0], results["documents"][0], results["metadatas"][0])
        ]
    
    
    
    """Searches for documents similar to the provided query text."""
    def get_all_documents(self) -> List[Dict[str, Any]]:
        results = self.collection.get()
        return [
            {
                "id": id,
                "content": doc,
                "url": meta["url"],
                "content_type": meta["content_type"]
            }
            for id, doc, meta in zip(results["ids"], results["documents"], results["metadatas"])
        ]
    

    """Retrieves all documents stored in the ChromaDB collection."""
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        try:
            results = self.collection.get(ids=[doc_id])
            if results and results["ids"]:
                return {
                    "id": results["ids"][0],
                    "content": results["documents"][0],
                    "url": results["metadatas"][0]["url"],
                    "content_type": results["metadatas"][0]["content_type"]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting document by ID: {str(e)}")
            return None


    """Retrieves a document by its unique ID from the ChromaDB collection."""
    async def generate_summary(self, doc_ids: List[str]) -> str:
        try:
            docs = self.collection.get(ids=doc_ids)
            if not docs or not docs["documents"]:
                return "Error: No documents found for the provided IDs"
            
            combined_content = "\n\n".join(docs["documents"])
            if not combined_content:
                return "Error: No content available to summarize"

            if not self.session_service or not self.text_agent:
                return "Error: Session service or text agent not available"

            # Create a session for the summary generation
            session = await self.session_service.create_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=f"summary_{doc_ids[0]}",
                state={"input_text": f"Summarize this content: {combined_content}"}
            )

            # Prepare content for the agent
            content = types.Content(role='user', parts=[types.Part(text=session.state["input_text"])])

            # Create proper InvocationContext
            invocation_context = InvocationContext(
                session=session,
                session_service=self.session_service,
                invocation_id=f"summary_{doc_ids[0]}",
                agent=self.text_agent,
                content=content
            )

            # Run the text agent
            events = self.text_agent.run_async(invocation_context)

            final_response = "No summary generated."
            async for event in events:
                if event.is_final_response() and event.content and event.content.parts:
                    final_response = event.content.parts[0].text
                    break

            return final_response
        except Exception as e:
            return f"Error generating summary: {str(e)}"
   
   
    """Generates a summary of the documents identified by the provided IDs using the text agent."""
    async def generate_podcast(self, doc_ids: List[str]) -> str:
        try:
            # Retrieve documents from ChromaDB
            docs = self.collection.get(ids=doc_ids)
            if not docs or not docs["documents"]:
                return "Error: No documents found for the provided IDs"
            
            combined_content = "\n\n".join(docs["documents"])
            if not combined_content:
                return "Error: No content available to generate podcast"

            if not self.session_service or not self.podcast_agent:
                return "Error: Session service or podcast agent not available"

            # Get or create session
            session = await self.session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID
            )
            if not session:
                session = await self.session_service.create_session(
                    app_name=APP_NAME,
                    user_id=USER_ID,
                    session_id=SESSION_ID,
                    state={"conversation_history": [], "input_text": "", "podcast_script": "", "generated_image": {}}
                )
            
            # Update session state with input
            session.state["input_text"] = combined_content
            session.state["processing_instructions"] = "Convert the provided text into engaging spoken audio using ElevenLabs TTS"
            
            # Prepare content for the agent
            content = types.Content(role='user', parts=[types.Part(text=f"Generate a podcast from this text: {combined_content}")])
            
            # Create proper InvocationContext
            invocation_context = InvocationContext(
                session=session,
                session_service=self.session_service,
                invocation_id=f"podcast_{doc_ids[0]}",
                agent=self.podcast_agent,
                content=content
            )
            
            # Run the podcast agent
            events = self.podcast_agent.run_async(invocation_context)
            
            # Collect response
            final_response = "No response captured."
            async for event in events:
                if event.is_final_response() and event.content and event.content.parts:
                    final_response = event.content.parts[0].text
                    break
            
            return final_response
        
        except Exception as e:
            
            return f"❌ Error generating podcast: {str(e)}"



    """Generates a podcast based on the content of the documents identified by the provided IDs."""
    async def generate_image(self, doc_ids: List[str]) -> str:
        try:
            docs = self.collection.get(ids=doc_ids)
            if not docs or not docs["documents"]:
                return "Error: No documents found for the provided IDs"
            
            combined_content = "\n\n".join(docs["documents"])
            if not combined_content:
                return "Error: No content available to generate image"

            if not self.session_service or not self.image_generation_agent:
                return "Error: Session service or image generation agent not available"

            # Create a session for image generation
            session = await self.session_service.create_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=f"image_{doc_ids[0]}",
                state={"input_text": f"Generate an image based on this content: {combined_content}"}
            )

            # Prepare content for the agent
            content = types.Content(role='user', parts=[types.Part(text=session.state["input_text"])])

            # Create proper InvocationContext
            invocation_context = InvocationContext(
                session=session,
                session_service=self.session_service,
                invocation_id=f"image_{doc_ids[0]}",
                agent=self.image_generation_agent,
                content=content
            )

            # Run the image generation agent
            events = self.image_generation_agent.run_async(invocation_context)

            final_response = "No image generated."
            async for event in events:
                if event.is_final_response() and event.content and event.content.parts:
                    final_response = event.content.parts[0].text
                    break

            return final_response
        except Exception as e:
            return f"Error generating image: {str(e)}"