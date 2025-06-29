import logging
import json
import re
from typing import AsyncGenerator, Dict, Any, List, Optional
from typing_extensions import override
from pydantic import BaseModel, Field
from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types
import asyncio

from level5.constants_and_models import RoutingDecision, APP_NAME, USER_ID, SESSION_ID
from level5.utils import ChromaDBManager, LinkProcessor
from level5.agents.llm_agents import (
    enhanced_router_agent, text_agent, image_agent, video_agent, audio_agent,
    realtime_audio_agent, podcast_agent, script_generator_agent, image_generation_agent
)

logger = logging.getLogger(__name__)

# --- Enhanced Multimodal Orchestrator Agent ---
class MultimodalOrchestratorAgent(BaseAgent):
    name: str
    text_agent: Any
    image_agent: Any
    video_agent: Any
    audio_agent: Any
    realtime_audio_agent: Any
    podcast_agent: Any
    script_generator_agent: Any
    image_generation_agent: Any
    router_agent: Any
    chroma_manager: Optional[ChromaDBManager] = None
    link_processor: Optional[LinkProcessor] = None

    model_config = {"arbitrary_types_allowed": True}

    def __init__(
        self,
        name: str,
        text_agent: Any,
        image_agent: Any,
        video_agent: Any,
        audio_agent: Any,
        realtime_audio_agent: Any,
        podcast_agent: Any,
        script_generator_agent: Any,
        image_generation_agent: Any,
        router_agent: Any,
        session_service: Any = None
    ):
        chroma_manager = ChromaDBManager(
            podcast_agent=podcast_agent,
            text_agent=text_agent,
            image_generation_agent=image_generation_agent,
            session_service=session_service
        )
        link_processor = LinkProcessor(chroma_manager)
        
        sub_agents_list = [
            router_agent,
            text_agent,
            image_agent,
            video_agent,
            audio_agent,
            realtime_audio_agent,
            podcast_agent,
            script_generator_agent,
            image_generation_agent
        ]
        super().__init__(
            name=name,
            text_agent=text_agent,
            image_agent=image_agent,
            video_agent=video_agent,
            audio_agent=audio_agent,
            realtime_audio_agent=realtime_audio_agent,
            podcast_agent=podcast_agent,
            script_generator_agent=script_generator_agent,
            image_generation_agent=image_generation_agent,
            router_agent=router_agent,
            sub_agents=sub_agents_list,
            chroma_manager=chroma_manager,
            link_processor=link_processor
        )

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        logger.info(f"[{self.name}] Starting enhanced multimodal processing workflow.")
        logger.info(f"[{self.name}] Running Router Agent...")
        
        # Check for link processing requests
        input_text = ctx.session.state.get("input_text", "")
        if input_text.startswith(("http://", "https://")):
            logger.info(f"[{self.name}] Processing URL: {input_text}")
            try:
                doc_id = self.link_processor.process_link(input_text)
                if doc_id:
                    ctx.session.state["last_processed_document_id"] = doc_id
                    logger.info(f"[{self.name}] Link processed successfully. Document ID: {doc_id}")
                    # Update input text to indicate successful processing
                    ctx.session.state["input_text"] = f"URL processed successfully. Document ID: {doc_id}. Please provide analysis instructions."
                else:
                    logger.error(f"[{self.name}] Failed to process URL: {input_text}")
                    error_response = f"❌ Failed to process URL: {input_text}"
                    yield Event(
                        content=types.Content(
                            role='assistant',
                            parts=[types.Part(text=error_response)]
                        ),
                        author=self.name
                    )
                    return
            except Exception as e:
                logger.error(f"[{self.name}] Error processing URL: {str(e)}")
                error_response = f"❌ Error processing URL: {str(e)}"
                yield Event(
                    content=types.Content(
                        role='assistant',
                        parts=[types.Part(text=error_response)]
                    ),
                    author=self.name
                )
                return

        # Check for summary requests
        if any(keyword in input_text.lower() for keyword in ["summarize", "summary", "summarize the above", "summarize this"]):
            last_doc_id = ctx.session.state.get("last_processed_document_id")
            if last_doc_id:
                logger.info(f"[{self.name}] Generating summary for document: {last_doc_id}")
                try:
                    # Get the document content
                    doc = self.chroma_manager.get_document_by_id(last_doc_id)
                    if doc:
                        # Update session state with document content for summarization
                        ctx.session.state["input_text"] = f"Summarize this content: {doc['content']}"
                        ctx.session.state["processing_instructions"] = "Generate a comprehensive summary of the provided content"
                        logger.info(f"[{self.name}] Document content loaded for summarization")
                    else:
                        logger.error(f"[{self.name}] Document not found: {last_doc_id}")
                        error_response = f"❌ Document not found: {last_doc_id}"
                        yield Event(
                            content=types.Content(
                                role='assistant',
                                parts=[types.Part(text=error_response)]
                            ),
                            author=self.name
                        )
                        return
                except Exception as e:
                    logger.error(f"[{self.name}] Error retrieving document for summary: {str(e)}")
                    error_response = f"❌ Error retrieving document: {str(e)}"
                    yield Event(
                        content=types.Content(
                            role='assistant',
                            parts=[types.Part(text=error_response)]
                        ),
                        author=self.name
                    )
                    return
            else:
                logger.warning(f"[{self.name}] Summary requested but no last processed document found")
                info_response = "ℹ️ No previous document found to summarize. Please process a link first."
                yield Event(
                    content=types.Content(
                        role='assistant',
                        parts=[types.Part(text=info_response)]
                    ),
                    author=self.name
                )
                return
        
        try:
            async for event in self.router_agent.run_async(ctx):
                logger.info(f"[{self.name}] Event from Router: {event.model_dump_json(indent=2, exclude_none=True)}")
                yield event
        except Exception as e:
            logger.error(f"[{self.name}] Error in router agent: {str(e)}")
            error_response = f"Error: Router agent failed: {str(e)}"
            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=error_response)]
                ),
                author=self.name
            )
            return

        routing_text = ctx.session.state.get("routing_decision", "")
        if not routing_text:
            logger.error(f"[{self.name}] No routing decision found. Aborting workflow.")
            error_response = "Error: No routing decision available."
            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=error_response)]
                ),
                author=self.name
            )
            return

        try:
            json_match = re.search(r'\{.*\}', routing_text, re.DOTALL)
            if json_match:
                routing_data = json.loads(json_match.group())
                routing_decision = RoutingDecision(**routing_data)
            else:
                raise ValueError("No valid JSON found in routing decision")
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse routing decision JSON: {e}")
            routing_decision = RoutingDecision(
                content_types=["text"],
                primary_agent="text",
                requires_multimodal=False,
                processing_plan="Process as text query",
                instructions="Provide a comprehensive response"
            )

        logger.info(f"[{self.name}] Routing decision: {routing_decision.model_dump()}")
        ctx.session.state["parsed_routing_decision"] = routing_decision.model_dump()
        if routing_decision.audio_config:
            ctx.session.state["audio_config"] = routing_decision.audio_config

        agent_map = {
            "text": self.text_agent,
            "image": self.image_agent,
            "video": self.video_agent,
            "audio": self.audio_agent,
            "realtime_audio": self.realtime_audio_agent,
            "podcast": self.podcast_agent,
            "script_generator": self.script_generator_agent,
            "image_generation": self.image_generation_agent
        }

        primary_agent = agent_map.get(routing_decision.primary_agent, self.text_agent)
        ctx.session.state["processing_instructions"] = routing_decision.instructions
        
        logger.info(f"[{self.name}] Running {primary_agent.name}...")
        try:
            async for event in primary_agent.run_async(ctx):
                logger.info(f"[{self.name}] Event from {primary_agent.name}: {event.model_dump_json(indent=2, exclude_none=True)}")
                yield event
                
                # Check if this is a summary request that needs document retrieval
                if (primary_agent.name == "TextAnalysisAgent" and 
                    "summarize" in routing_decision.instructions.lower() and
                    ("last processed document" in routing_decision.instructions.lower() or 
                     "session state" in routing_decision.instructions.lower())):
                    
                    logger.info(f"[{self.name}] Detected summary request. Checking session state...")
                    logger.info(f"[{self.name}] Session state keys: {list(ctx.session.state.keys())}")
                    
                    # Check if we have a last processed document
                    last_doc_id = ctx.session.state.get("last_processed_document_id")
                    logger.info(f"[{self.name}] Last processed doc_id: {last_doc_id}")
                    
                    if last_doc_id and self.chroma_manager:
                        logger.info(f"[{self.name}] Fetching and summarizing document {last_doc_id}")
                        
                        try:
                            # Fetch the document content
                            docs = self.chroma_manager.collection.get(ids=[last_doc_id])
                            logger.info(f"[{self.name}] Retrieved docs: {docs is not None}")
                            
                            if docs and docs["documents"]:
                                content = docs["documents"][0]
                                url = docs["metadatas"][0]["url"] if docs["metadatas"] else "Unknown source"
                                
                                logger.info(f"[{self.name}] Document content length: {len(content)}")
                                
                                # Create a summary request
                                summary_instruction = f"Summarize the following article from {url}:\n\n{content[:2000]}{'...' if len(content) > 2000 else ''}"
                                ctx.session.state["input_text"] = summary_instruction
                                ctx.session.state["processing_instructions"] = "Provide a comprehensive summary of the article"
                                
                                # Run the text agent again with the document content
                                logger.info(f"[{self.name}] Running summary generation...")
                                async for summary_event in self.text_agent.run_async(ctx):
                                    logger.info(f"[{self.name}] Summary event: {summary_event.model_dump_json(indent=2, exclude_none=True)}")
                                    yield summary_event
                            else:
                                error_response = "Error: Could not retrieve the last processed document for summarization."
                                logger.error(f"[{self.name}] {error_response}")
                                yield Event(
                                    content=types.Content(
                                        role='assistant',
                                        parts=[types.Part(text=error_response)]
                                    ),
                                    author=self.name
                                )
                        except Exception as e:
                            logger.error(f"[{self.name}] Error summarizing document: {str(e)}")
                            error_response = f"Error: Failed to summarize the document: {str(e)}"
                            yield Event(
                                content=types.Content(
                                    role='assistant',
                                    parts=[types.Part(text=error_response)]
                                ),
                                author=self.name
                            )
                    else:
                        error_response = "No document has been processed yet. Please process a link first before requesting a summary."
                        logger.warning(f"[{self.name}] {error_response}")
                        yield Event(
                            content=types.Content(
                                role='assistant',
                                parts=[types.Part(text=error_response)]
                            ),
                            author=self.name
                        )
                        
        except Exception as e:
            logger.error(f"[{self.name}] Error in {primary_agent.name}: {str(e)}")
            error_response = f"Error: {primary_agent.name} failed: {str(e)}"
            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=error_response)]
                ),
                author=self.name
            )

        if routing_decision.primary_agent == "podcast" and not ctx.session.state.get("podcast_script"):
            logger.info(f"[{self.name}] No script found for podcast generation. Generating script first.")
            ctx.session.state["processing_instructions"] = "Generate an engaging podcast script based on the provided topic"
            try:
                async for event in self.script_generator_agent.run_async(ctx):
                    logger.info(f"[{self.name}] Event from ScriptGeneratorAgent: {event.model_dump_json(indent=2, exclude_none=True)}")
                    yield event
            except Exception as e:
                logger.error(f"[{self.name}] Error in ScriptGeneratorAgent: {str(e)}")
                error_response = f"Error: Script generation failed: {str(e)}"
                yield Event(
                    content=types.Content(
                        role='assistant',
                        parts=[types.Part(text=error_response)]
                    ),
                    author=self.name
                )

        if ctx.session.state.get("podcast_script"):
            logger.info(f"[{self.name}] Triggering podcast generation with generated script.")
            ctx.session.state["processing_instructions"] = "Convert the generated script into spoken audio"
            try:
                async for event in self.podcast_agent.run_async(ctx):
                    logger.info(f"[{self.name}] Event from PodcastGeneratorAgent: {event.model_dump_json(indent=2, exclude_none=True)}")
                    yield event
            except Exception as e:
                logger.error(f"[{self.name}] Error in PodcastGeneratorAgent: {str(e)}")
                error_response = f"Error: Podcast generation failed: {str(e)}"
                yield Event(
                    content=types.Content(
                        role='assistant',
                        parts=[types.Part(text=error_response)]
                    ),
                    author=self.name
                )

        logger.info(f"[{self.name}] Enhanced multimodal workflow completed.")

    @override
    async def _run_live_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        logger.info(f"[{self.name}] Starting live session.")
        try:
            welcome_message = """
🎬 **Multimodal Orchestrator Live Session Started**

I'm ready to help you with:
- 📝 Podcast script generation
- 🎙️ Podcast audio generation
- 🖼️ Image generation
- 🎵 Audio analysis and processing
- 🖼️ Image analysis and understanding
- 📊 Data visualization and insights
- 🤖 Real-time multimodal workflows
- 🔗 Link processing and content extraction
- 📄 Document summarization

Send me your files or messages, and I'll coordinate the appropriate specialized agents!
            """.strip()
            
            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=welcome_message)]
                ),
                author=self.name
            )
            
            while True:
                if hasattr(ctx, 'content') and ctx.content:
                    async for event in self._run_async_impl(ctx):
                        yield event
                    break
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"[{self.name}] Error in live session: {e}")
            error_message = f"❌ Live session error: {str(e)}"
            yield Event(
                content=types.Content(
                    role='assistant',
                    parts=[types.Part(text=error_message)]
                ),
                author=self.name
            )