from agno.team import Team
from textwrap import dedent
from agno.models.google import Gemini
from agents.podcast_speakers import create_speaker_a, create_speaker_b
from agno.utils.log import logger

# Create a team for podcast conversations
# This team includes two speakers who engage in a collaborative dialogue based on a given topic.
def create_podcast_team():
    speaker_a = create_speaker_a()
    speaker_b = create_speaker_b()
    return Team(
        name="Podcast Conversation Team",
        mode="collaborate",
        model=Gemini(),
        members=[speaker_a, speaker_b],
        instructions=[
            dedent("""
                Generate a 100-word podcast conversation based on the provided topic, ensuring equal participation and natural dialogue.
                Format each speaker's line as 'SPEAKER_A:' or 'SPEAKER_B:' followed by their dialogue.
                Ensure each line starts with the speaker label and contains no more than 20 words.
                Do not include outer music or intro, just the conversation.
                If the topic includes a URL, summarize its content and base the conversation on that summary.
                Log the topic and summary for debugging.
            """)
        ],
        show_members_responses=True,
        debug_mode=True,
    )