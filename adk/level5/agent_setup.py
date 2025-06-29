import logging
import json
import asyncio
from typing import Optional
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
from google.adk.agents.invocation_context import InvocationContext
from level5.agents import (
    enhanced_router_agent,
    text_agent,
    image_agent,
    video_agent,
    audio_agent,
    realtime_audio_agent,
    podcast_agent,
    script_generator_agent,
    image_generation_agent,
    MultimodalOrchestratorAgent
)
from level5.constants_and_models import APP_NAME, USER_ID, SESSION_ID, INITIAL_STATE
from level5.utils import get_system_info

logger = logging.getLogger(__name__)

# --- Setup Session and Runner ---
session_service = InMemorySessionService()

# --- Create the Enhanced Orchestrator Agent Instance ---
multimodal_orchestrator = MultimodalOrchestratorAgent(
    name="MultimodalOrchestratorAgent",
    text_agent=text_agent,
    image_agent=image_agent,
    video_agent=video_agent,
    audio_agent=audio_agent,
    realtime_audio_agent=realtime_audio_agent,
    podcast_agent=podcast_agent,
    script_generator_agent=script_generator_agent,
    image_generation_agent=image_generation_agent,
    router_agent=enhanced_router_agent,
    session_service=session_service
)

runner = Runner(
    agent=multimodal_orchestrator,
    app_name=APP_NAME,
    session_service=session_service
)

async def initialize_session():
    """Initialize a new session with the proper initial state."""
    try:
        session = session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
            state=INITIAL_STATE
        )
        logger.info(f"Initial session state: {session.state}")
        logger.info(f"Session object type: {type(session)} value: {session}")
        print(f"[DEBUG] Initial session state: {session.state}")
        print(f"[DEBUG] Session object type: {type(session)} value: {session}")
        return session
    except Exception as e:
        logger.error(f"Exception in initialize_session: {e}")
        print(f"[DEBUG] Exception in initialize_session: {e}")
        return None

async def call_agent(query: str, audio_file_path: Optional[str] = None):
    try:
        # Get the most recent session state
        current_session = session_service.get_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID
        )
        logger.info(f"call_agent: get_session returned type: {type(current_session)} value: {current_session}")
        print(f"[DEBUG] call_agent: get_session returned type: {type(current_session)} value: {current_session}")
        
        if not current_session:
            logger.warning("Session not found, creating new one")
            print("[DEBUG] Session not found, creating new one")
            current_session = await initialize_session()
            if not current_session:
                logger.error("Failed to get or create session! (call_agent)")
                print("[DEBUG] Failed to get or create session! (call_agent)")
                return "Error: Could not initialize session"

        # Update session state with the new query
        current_session.state["input_text"] = query
        if audio_file_path:
            current_session.state["audio_file_path"] = audio_file_path

        # Log the current session state for debugging
        logger.info(f"call_agent: Current session state keys: {list(current_session.state.keys())}")
        if "last_processed_doc_id" in current_session.state:
            logger.info(f"call_agent: Found last_processed_doc_id: {current_session.state['last_processed_doc_id']}")

        content = types.Content(role='user', parts=[types.Part(text=query)])
        events = runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)

        final_response = "No final response captured."
        for event in events:
            if event.is_final_response() and event.content and event.content.parts:
                logger.info(f"Final response from [{event.author}]: {event.content.parts[0].text}")
                final_response = event.content.parts[0].text

        print("\n--- Enhanced Multimodal Agent Response ---")
        print("Agent Final Response:", final_response)

        try:
            final_session = session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID
            )
            if final_session:
                print("\nFinal Session State:")
                print(json.dumps(final_session.state, indent=2))
        except Exception as e:
            logger.warning(f"Could not retrieve final session state: {e}")
        
        print("------------------------------------------\n")
        return final_response
    except Exception as e:
        logger.error(f"Error in call_agent: {e}")
        return f"Error: {str(e)}" 