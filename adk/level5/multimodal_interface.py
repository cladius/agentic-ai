import logging
import json
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from google.genai import types
from level5.agent_setup import (
    session_service, runner, call_agent, initialize_session,
    multimodal_orchestrator, realtime_audio_agent, podcast_agent,
    script_generator_agent, image_generation_agent, enhanced_router_agent,
    text_agent, image_agent, video_agent, audio_agent
)
from level5.constants_and_models import APP_NAME, USER_ID, SESSION_ID, INITIAL_STATE
from level5.utils import ChromaDBManager, LinkProcessor, AudioUtils, AudioConfig

logger = logging.getLogger(__name__)

# --- Enhanced Interactive Interface ---
class MultimodalAgentInterface:
    def __init__(self):
        self.session_service = session_service
        self.runner = runner
        self.podcast_agent = podcast_agent
        self.chroma_manager = ChromaDBManager(
            podcast_agent=self.podcast_agent,
            text_agent=text_agent,
            image_generation_agent=image_generation_agent,
            session_service=session_service
        )
        self.link_processor = LinkProcessor(self.chroma_manager)

    async def chat(self, query: str, audio_file_path: Optional[str] = None) -> str:
        return await call_agent(query, audio_file_path)

    async def process_audio_file(self, audio_file_path: str, query: str = "Analyze this audio file") -> str:
        if not Path(audio_file_path).exists():
            return f"Error: Audio file not found at {audio_file_path}"
        return await self.chat(query, audio_file_path)

    async def start_realtime_audio(self, query: str = "Start real-time audio processing") -> str:
        return await self.chat(f"real-time audio: {query}")

    async def generate_podcast(self, text: str) -> str:
        try:
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
                    state=INITIAL_STATE
                )

            session.state["input_text"] = text
            logger.info(f"Stored input_text in session state: {text[:50]}{'...' if len(text) > 50 else ''}")

            podcast_query = f"Generate a podcast from this text: {text}"
            content = types.Content(role='user', parts=[types.Part(text=podcast_query)])
            events = self.runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)

            final_response = "No response captured."
            for event in events:
                if event.is_final_response() and event.content and event.content.parts:
                    logger.info(f"[{event.author}]: {event.content.parts[0].text}")
                    final_response = event.content.parts[0].text

            return final_response
            
        except Exception as e:
            logger.error(f"Error generating podcast: {str(e)}")
            return f"Error: {str(e)}"

    async def generate_podcast_script(self, topic: str) -> str:
        try:
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
                    state=INITIAL_STATE
                )
            
            session.state["input_text"] = f"Generate a podcast script about {topic}"
            session.state["podcast_script"] = ""
            logger.info(f"Stored topic in session state: {topic[:50]}{'...' if len(topic) > 50 else ''}")
            
            script_query = f"Generate a podcast script about {topic}"
            content = types.Content(role='user', parts=[types.Part(text=script_query)])
            events = self.runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)
            
            final_response = "No response captured."
            for event in events:
                if event.is_final_response() and event.content and event.content.parts:
                    logger.info(f"[{event.author}]: {event.content.parts[0].text}")
                    final_response = event.content.parts[0].text
            
            return final_response
        except Exception as e:
            logger.error(f"Error generating podcast script: {str(e)}")
            return f"Error: {str(e)}"

    async def generate_image(self, description: str) -> str:
        try:
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
                    state=INITIAL_STATE
                )

            session.state["input_text"] = f"Generate an image of {description}"
            logger.info(f"Stored image description in session state: {description[:50]}{'...' if len(description) > 50 else ''}")

            content = types.Content(role='user', parts=[types.Part(text=f"Generate an image of {description}")])
            events = self.runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)

            final_response = "No response captured."
            for event in events:
                if event.is_final_response() and event.content and event.content.parts:
                    logger.info(f"[{event.author}]: {event.content.parts[0].text}")
                    final_response = event.content.parts[0].text

            return final_response
        
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            return f"Error: {str(e)}"

    async def get_conversation_history(self) -> List[Dict[str, Any]]:
        try:
            current_session = await self.session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID
            )
            if current_session:
                return current_session.state.get("conversation_history", [])
            return []
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []

    async def clear_history(self):
        try:
            current_session = await self.session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID
            )
            if current_session:
                current_session.state["conversation_history"] = []
        except Exception as e:
            logger.error(f"Error clearing history: {e}")

    async def process_link(self, url: str) -> str:
        try:
            doc_id = self.link_processor.process_link(url)
            if doc_id:
                return f"✅ Link processed successfully. Document ID: {doc_id}"
            return "❌ Failed to process link"
        except Exception as e:
            return f"❌ Error processing link: {str(e)}"

    async def search_stored_data(self, query: str) -> str:
        try:
            results = self.chroma_manager.search_similar(query)
            if results:
                return "\n".join([f"📄 {doc['id']}: {doc['content'][:100]}..." for doc in results])
            return "No matching documents found"
        except Exception as e:
            return f"❌ Error searching data: {str(e)}"

    async def list_stored_data(self) -> str:
        try:
            results = self.chroma_manager.get_all_documents()
            if results:
                return "\n".join([f"📄 {doc['id']}: {doc['url']}" for doc in results])
            return "No documents stored"
        except Exception as e:
            return f"❌ Error listing data: {str(e)}"

    async def generate_summary(self, doc_ids: List[str]) -> str:
        try:
            return await self.chroma_manager.generate_summary(doc_ids)
        except Exception as e:
            return f"❌ Error generating summary: {str(e)}"

    async def generate_podcast_from_data(self, doc_ids: List[str]) -> str:
        try:
            return await self.chroma_manager.generate_podcast(doc_ids)
        except Exception as e:
            return f"❌ Error generating podcast: {str(e)}"

    async def generate_image_from_data(self, doc_ids: List[str]) -> str:
        try:
            return await self.chroma_manager.generate_image(doc_ids)
        except Exception as e:
            return f"❌ Error generating image: {str(e)}"

    async def interactive_mode(self):
        print("🤖 Enhanced Multimodal AI Agent System")
        print("=" * 70)
        print("Available capabilities:")
        print("- Text processing and analysis")
        print("- Audio file processing")
        print("- Real-time audio processing")
        print("- Podcast generation")
        print("- Podcast script generation")
        print("- Image generation")
        print("- Link processing and storage")
        print("- Data retrieval and analysis")
        print("=" * 70)
        print("\nSpecial commands for link processing:")
        print("- process <url> - Process and store a link")
        print("- search <query> - Search stored data")
        print("- list - List all stored documents")
        print("- summary <doc_id1,doc_id2,...> - Generate summary from documents")
        print("- podcast <doc_id1,doc_id2,...> - Generate podcast from documents")
        print("- image <doc_id1,doc_id2,...> - Generate image from documents")
        print("=" * 70)

        while True:
            try:
                user_input = input("\nYou: ").strip()

                if user_input.lower() == "exit":
                    print("Goodbye! 👋")
                    break
                elif not user_input:
                    print("❌ Please enter a query.")
                    continue

                if user_input.startswith("process "):
                    url = user_input[8:].strip()
                    response = await self.process_link(url)
                elif user_input.startswith("search "):
                    query = user_input[7:].strip()
                    response = await self.search_stored_data(query)
                elif user_input.lower() == "list":
                    response = await self.list_stored_data()
                elif user_input.startswith("summary "):
                    doc_ids = user_input[8:].strip().split(",")
                    response = await self.generate_summary(doc_ids)
                elif user_input.startswith("podcast "):
                    doc_ids = user_input[8:].strip().split(",")
                    response = await self.generate_podcast_from_data(doc_ids)
                elif user_input.startswith("image "):
                    doc_ids = user_input[6:].strip().split(",")
                    response = await self.generate_image_from_data(doc_ids)
                else:
                    print("\n🔄 Processing...")
                    response = await self.chat(user_input)
                
                print(f"\n🤖 Response:")
                print(f"{response}")

            except KeyboardInterrupt:
                print("\n\nGoodbye! 👋")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {str(e)}")
                logger.error(f"Unexpected error in interactive mode: {str(e)}")

# --- API-like Functions for Integration ---
class MultimodalAPI:
    def __init__(self):
        self.interface = MultimodalAgentInterface()
        from utils import AudioProcessor
        self.audio_processor = AudioProcessor()
    
    def process_text(self, text: str) -> Dict[str, Any]:
        try:
            response = asyncio.run(self.interface.chat(text))
            return {
                "success": True,
                "response": response,
                "type": "text",
                "timestamp": str(asyncio.get_event_loop().time())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "type": "text"
            }
    
    def process_audio_file(self, file_path: str, instructions: str = "Analyze this audio") -> Dict[str, Any]:
        try:
            validation = AudioUtils.validate_audio_file(file_path)
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": validation["error"],
                    "type": "audio"
                }
            response = asyncio.run(self.interface.process_audio_file(file_path, instructions))
            return {
                "success": True,
                "response": response,
                "type": "audio",
                "file_info": validation,
                "timestamp": str(asyncio.get_event_loop().time())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "type": "audio"
            }
    
    def start_realtime_audio_session(self, config: Optional[AudioConfig] = None) -> Dict[str, Any]:
        try:
            if config is None:
                config = AudioUtils.create_test_audio_config()
                config.realtime = True
            response = asyncio.run(self.interface.start_realtime_audio())
            return {
                "success": True,
                "response": response,
                "type": "realtime_audio",
                "config": config.dict(),
                "timestamp": str(asyncio.get_event_loop().time())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "type": "realtime_audio"
            }
    
    def generate_podcast(self, text: str) -> Dict[str, Any]:
        try:
            response = asyncio.run(self.interface.generate_podcast(text))
            return {
                "success": True,
                "response": response,
                "type": "speech_generation",
                "timestamp": str(asyncio.get_event_loop().time())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "type": "speech_generation"
            }
    
    def generate_podcast_script(self, topic: str) -> Dict[str, Any]:
        try:
            response = asyncio.run(self.interface.generate_podcast_script(topic))
            return {
                "success": True,
                "response": response,
                "type": "script_generation",
                "timestamp": str(asyncio.get_event_loop().time())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "type": "script_generation"
            }
    
    def generate_image(self, description: str) -> Dict[str, Any]:
        try:
            response = asyncio.run(self.interface.generate_image(description))
            return {
                "success": True,
                "response": response,
                "type": "image_generation",
                "timestamp": str(asyncio.get_event_loop().time())
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "type": "image_generation"
            }
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        return {
            "audio": [".wav", ".mp3", ".m4a", ".aac"],
            "video": [".mp4", ".avi", ".mov", ".mkv"],
            "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
            "text": ["plain text", "markdown", "json"],
            "speech_generation": ["text"],
            "script_generation": ["text"],
            "image_generation": ["text"]
        }

def get_system_info() -> Dict[str, Any]:
    return {
        "agents": {
            "text": "TextAnalysisAgent",
            "image": "ImageAnalysisAgent",
            "video": "VideoAnalysisAgent",
            "audio": "AudioAnalysisAgent",
            "realtime_audio": "RealtimeAudioAgent",
            "podcast": "PodcastGeneratorAgent",
            "script_generator": "ScriptGeneratorAgent",
            "image_generation": "ImageGenerationAgent"
        },
        "models": {
            "primary": "gemini-2.0-flash-exp",
            "router": "gemini-1.5-flash",
            "live": "gemini-2.0-flash-live-001",
            "image_generation": "gemini-2.0-flash-preview-image-generation"
        },
        "audio_config": {
            "sample_rate": 16000,
            "bit_depth": 16,
            "channels": 1
        },
        "supported_formats": MultimodalAPI().get_supported_formats()
    }