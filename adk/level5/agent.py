import asyncio
import logging
import sys


"""This module serves as the main entry point for the Level 5 multimodal agent system, initializing the session and starting the interactive interface."""
from level5.agent_setup import (
    runner,
    session_service,
    call_agent,
    initialize_session,
    multimodal_orchestrator,
    realtime_audio_agent,
    podcast_agent,
    script_generator_agent,
    image_generation_agent,
    enhanced_router_agent,
    text_agent,
    image_agent,
    video_agent,
    audio_agent
)
from level5.constants_and_models import APP_NAME, USER_ID, SESSION_ID, INITIAL_STATE
from level5.multimodal_interface import MultimodalAgentInterface



logger = logging.getLogger(__name__)



"""This module provides the setup for the Level 5 multimodal agent system, including the creation of agents and the runner."""
# --- Export root agent ---
root_agent = multimodal_orchestrator

# --- Export for use in other modules ---
__all__ = [
    "runner",
    "session_service",
    "call_agent",
    "multimodal_orchestrator",
    "realtime_audio_agent",
    "podcast_agent",
    "script_generator_agent",
    "image_generation_agent",
    "enhanced_router_agent",
    "text_agent",
    "image_agent",
    "video_agent",
    "audio_agent"
]


"""This module serves as the main entry point for the Level 5 multimodal agent system."""
async def main():
    try:
        print('[DEBUG] Entered __main__')
        
        # Initialize session before starting interface
        session = await initialize_session()
        if not session:
            print("Error: Failed to initialize session.")
            sys.exit(1)

        interface = MultimodalAgentInterface()
        await interface.interactive_mode()

        sys.exit(0)
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        
        sys.exit(1)

"""This is the main entry point for the Level 5 multimodal agent system."""
if __name__ == "__main__":
    asyncio.run(main())
