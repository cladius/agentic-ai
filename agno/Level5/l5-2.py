'''
Level 5 - Multi-Source Processor with Podcast Generation
This module implements a multi-source content processing workflow that extracts information from PDFs, YouTube videos, webpages, and text inputs. 
It generates a podcast conversation between two speakers based on the processed content.'''
import os
import json
from uuid import uuid4
from dotenv import load_dotenv
from agno.tools.youtube import YouTubeTools
from agno.agent import Agent, RunResponse
from agno.models.google import Gemini
from agno.tools.eleven_labs import ElevenLabsTools
from agno.tools.website import WebsiteTools
from agno.team import Team
from agno.workflow.workflow import Workflow
from agno.utils.log import logger
from agno.knowledge.pdf_url import PDFUrlKnowledgeBase, PDFUrlReader
from agno.vectordb.chroma import ChromaDb
from agno.embedder.google import GeminiEmbedder
from agno.playground import Playground, serve_playground_app
from pydub import AudioSegment
from io import BytesIO
import base64

# Load environment variables
load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["ELEVEN_LABS_API_KEY"] = os.getenv("ELEVEN_LABS_API_KEY")
embedder = GeminiEmbedder(api_key=os.getenv("GOOGLE_API_KEY"))

PDFUrlReader.separators = ["\n\n", "\n", ".", " "]

class MultiSourceWorkflow(Workflow):
    """
    A workflow that processes content from multiple sources (PDFs, YouTube videos, webpages, and text),
    answers questions based on the content, and generates a podcast with dialogues between two individuals.
    """

    def _initialize_knowledge_base(self, agent_name: str, collection_name: str, urls: list = None):
        """
        Initialize a knowledge base for the specified agent.

        Args:
            agent_name (str): Name of the agent ('pdf_agent').
            collection_name (str): Name of the vector DB collection.
            urls (list, optional): List of URLs to initialize the knowledge base with.

        Returns:
            KnowledgeBase: Initialized knowledge base instance.

        Raises:
            ValueError: If agent_name is invalid.
            RuntimeError: If initialization fails.
        """
        try:
            vector_db = ChromaDb(collection=collection_name, embedder=embedder)
            vector_db.client.get_or_create_collection(collection_name)
            if agent_name == "pdf_agent":
                return PDFUrlKnowledgeBase(
                    urls=urls or [],
                    vector_db=vector_db,
                    embedder=embedder,
                    reader=PDFUrlReader(),
                )
            else:
                raise ValueError(f"Invalid agent_name: {agent_name}")
        except Exception as e:
            logger.error(f"Failed to initialize knowledge base for {agent_name}: {str(e)}")
            raise RuntimeError(f"Knowledge base initialization failed: {str(e)}")

    # Define agents and teams
    # URL Handler agent extracts URLs, classifies them, and returns a structured JSON response.
    url_handler_agent = Agent(
        agent_id="url-handler",
        name="URL Handler",
        model=Gemini(),
        instructions=[
            """
            You are a URL classification agent. Your task is to extract URLs from a prompt, classify them, and return a valid JSON string. Follow these steps:

            1. Extract URLs using regex: (?:https?://|www\\.)[^\\s<>']+|[^\\s<>']+\\.(?:com|org|net|edu|gov|io)[^\\s<>']*
            2. Normalize URLs:
               - Add "https://" if no scheme (e.g., www.example.com -> https://www.example.com).
               - Append ".com" if no top-level domain, unless it's "youtu.be".
            3. Classify URLs:
               - "pdf": Ends with .pdf.
               - "youtube": Contains "youtube.com" or "youtu.be" with a video ID.
               - "webpage": All other valid URLs.
            4. Extract remaining text by removing URLs.
            5. Return a JSON string with this exact structure:
            {"pdf_urls":[],"youtube_urls":[],"web_urls":[],"remaining_text":"string","errors":"array"}

            CRITICAL:
            - Output ONLY a valid JSON string (e.g., {"key":"value"}).
            - Ensure all brackets and quotes are properly closed.
            - NO Markdown (e.g., ```json), comments, or nested objects.
            - Validate JSON syntax before returning.
            - If no URLs are found, include "No valid URLs found" in errors but proceed.

            Examples:
            Input: "summarize https://example.com/doc.pdf"
            Output: {"pdf_urls":["https://example.com/doc.pdf"],"youtube_urls":[],"web_urls":[],"remaining_text":"summarize","errors":[]}

            Input: "summarize the"
            Output: {"pdf_urls":[],"youtube_urls":[],"web_urls":[],"remaining_text":"summarize the","errors":["No valid URLs found"]}
            """
        ],
        debug_mode=True,
    )

    # JSON Corrector agent , which fixes malformed JSON output from the URL Handler agent.
    json_corrector_agent = Agent(
        agent_id="json-corrector",
        name="JSON Corrector",
        model=Gemini(),
        instructions=[
            """
            You are a JSON correction agent. Your task is to fix malformed JSON output from the URL Handler agent and return a valid JSON string matching:

            {"pdf_urls":[],"youtube_urls":[],"web_urls":[],"remaining_text":"string","errors":"array"}

            Steps:
            1. Receive the URL Handler's output.
            2. If valid JSON and matches the structure, return it unchanged.
            3. If wrapped in Markdown (e.g., ```json ... ```), strip Markdown and validate.
            4. If malformed (e.g., unclosed brackets, nested objects), fix by:
               - Closing unclosed brackets or quotes.
               - Removing nested objects, keeping the first valid set of "pdf_urls", "youtube_urls", etc.
               - Ensuring all fields are present with default values if missing.
            5. If correction fails, return:
            {"pdf_urls":[],"youtube_urls":[],"web_urls":[],"remaining_text":"","errors":["Failed to correct JSON"]}

            CRITICAL:
            - Output ONLY a valid JSON string.
            - NO Markdown (e.g., ```json ... ```), comments, or explanations.
            - Ensure proper bracket and quote closure.
            - If no URLs are found, pass the valid JSON unchanged.

            Examples:
            Input: ```json\n{"pdf_urls":["https://example.com/doc.pdf"],"youtube_urls":[],"web_urls":[],"remaining_text":"summarize","errors":[]}\n```
            Output: {"pdf_urls":["https://example.com/doc.pdf"],"youtube_urls":[],"web_urls":[],"remaining_text":"summarize","errors":[]}

            Input: invalid
            Output: {"pdf_urls":[],"youtube_urls":[],"web_urls":[],"remaining_text":"","errors":["Failed to correct JSON"]}
            """
        ],
        debug_mode=True,
    )

    # Scraper agent scrapes content from webpages and returns raw text.
    scraper_agent = Agent(
        name="Content Scraper",
        model=Gemini(),
        tools=[WebsiteTools()],
        instructions=[
            "Scrape the content of the given URL and return the raw text.",
            "If error, return: 'Failed to process webpage content: {content}'."
        ],
        debug_mode=True,
    )

    # PDF agent processes PDF URLs, extracts content, and stores it in a knowledge base.
    pdf_agent = Agent(
        name="PDF Processor",
        model=Gemini(),
        knowledge=None,  # Updated in __init__
        search_knowledge=True,
        tools=[PDFUrlReader()],
        instructions=[
            "Query the knowledge base for PDF content at the provided URL.",
            "Summarize or answer questions (max 1500 characters).",
            "If query fails, return: 'Failed to process PDF: {error}'."
        ],
        debug_mode=True,
    )

    # YouTube agent processes YouTube video URLs, retrieves captions, and summarizes content.
    youtube_agent = Agent(
        name="YouTube Processor",
        model=Gemini(),
        tools=[YouTubeTools(get_video_captions=True)],
        instructions=[
            "Get YouTube video captions for the provided URL.",
            "Summarize or answer questions based on the transcript or captions(max 1500 characters).",
            "If no transcript, return: 'No transcript available for {url}.'"
        ],
        debug_mode=True,
    )

    # Webpage agent processes general webpage content, summarizing or answering questions.
    web_agent = Agent(
        name="Webpage Processor",
        model=Gemini(),
        instructions=[
            "Process webpage content, summarize or answer questions (max 1500 characters).",
            "If error, return: 'Failed to process webpage content: {content}'."
        ],
        debug_mode=True,
    )

    # Text agent processes plain text input, summarizing or answering questions.
    text_agent = Agent(
        name="Text Processor",
        model=Gemini(),
        instructions=[
            """
            Process plain text input. Summarize or answer questions (max 1500 characters).
            If podcast request, return: 'Podcast request should be handled by Podcast Conversation Team.'
            """
        ],
        debug_mode=True,
    )

    # Podcast Conversation Team generates a podcast conversation between two speakers.
    speaker_a = Agent(
        name="Speaker A - Tech Expert",
        role="Technology expert and podcast host",
        model=Gemini(),
        instructions=[
            """
            SPEAKER_A: Limit to 20 words, ask questions or comment on content.
            """
        ],
        debug_mode=True,
    )

    speaker_b = Agent(
        name="Speaker B - Industry Analyst",
        role="Industry analyst and guest expert",
        model=Gemini(),
        instructions=[
            """
            SPEAKER_B: Limit to 20 words, provide data-driven insights.
            """
        ],
        debug_mode=True,
    )

    # Podcast Conversation Team collaborates to generate a podcast conversation.
    podcast_conversation_team = Team(
        name="Podcast Conversation Team",
        mode="collaborate",
        model=Gemini(),
        members=[speaker_a, speaker_b],
        instructions=[
            "Generate a 100-word podcast conversation, equal participation, natural dialogue.",
            "Format each speaker's line as 'SPEAKER_A:' or 'SPEAKER_B:' followed by their dialogue.",
            "Ensure each line starts with the speaker label and contains no more than 20 words.",
            "do not include outer music and intro, just the conversation."
        ],
        show_members_responses=True,
        debug_mode=True,
    )

    # MultiSource Processor Team routes tasks to appropriate agents based on content type.
    team = Team(
        name="MultiSource Processor & Podcast Team",
        mode="route",
        model=Gemini(),
        show_members_responses=True,
        enable_agentic_context=True,
        show_tool_calls=True,
        monitoring=True,
        members=[
            url_handler_agent,
            json_corrector_agent,
            scraper_agent,
            pdf_agent,
            youtube_agent,
            web_agent,
            text_agent,
            podcast_conversation_team,
        ],
        instructions=[
            """
            Route tasks:
            1. URL Handler extracts URLs.
            2. JSON Corrector fixes JSON.
            3. Route PDFs to PDF Processor, YouTube to YouTube Processor, webpages to Webpage Processor.
            4. Route text to Text Processor unless it's a podcast request.
            5. Podcast requests go to Podcast Conversation Team.
            """
        ]
    )

    def __init__(self, *args, **kwargs):
        """
        Initialize the workflow with knowledge bases and voice configurations.
        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        Raises:
            ValueError: If the team name or mode is invalid.
            RuntimeError: If knowledge base initialization fails.
        """
        super().__init__(*args, **kwargs)
        self.voice_configs = {
            "SPEAKER_A": "JBFqnCBsd6RMkjVDRZzb",  # Male voice
            "SPEAKER_B": "21m00Tcm4TlvDq8ikWAM",  # Female voice (Rachel)
        }

        # Initialize knowledge bases
        self.pdf_knowledge_base = self._initialize_knowledge_base(
            agent_name="pdf_agent",
            collection_name="pdf_content",
        )

        # Update agents' knowledge bases
        self.pdf_agent.knowledge = self.pdf_knowledge_base
        
        logger.info(f"Team Configuration - Name: {self.team.name}, Mode: {self.team.mode}")

    def generate_conversation(self, topic: str) -> str:
        """Generate the podcast conversation between two speakers based on the given topic.
        Args:
            topic (str): The topic for the podcast conversation.    
        Returns:
            str: The generated conversation formatted with speaker labels.
        """
        print(f"🎙️ Generating conversation about: {topic}")
        response = self.podcast_conversation_team.run(
            f"Create a 30-second podcast episode about {topic}. "
            f"Make it engaging and ensure both speakers participate equally."
        )
        return response.content if response else ""

    def parse_conversation_segments(self, conversation: str) -> list:
        """Parse conversation into sequential segments with speaker identification.
        Args:
            conversation (str): The conversation text with speaker labels.
        Returns:
            list: A list of segments with speaker, text, and voice_id.
        Raises:
            ValueError: If the conversation format is invalid.
        """
        segments = []
        lines = conversation.split('\n')
        current_speaker = None
        current_text = ""

        for line in lines:
            line = line.strip()
            if line.startswith("SPEAKER_A:"):
                if current_speaker and current_text.strip():
                    segments.append({
                        'speaker': current_speaker,
                        'text': current_text.strip(),
                        'voice_id': self.voice_configs[current_speaker]
                    })
                current_speaker = "SPEAKER_A"
                current_text = line.replace("SPEAKER_A:", "").strip()
            elif line.startswith("SPEAKER_B:"):
                if current_speaker and current_text.strip():
                    segments.append({
                        'speaker': current_speaker,
                        'text': current_text.strip(),
                        'voice_id': self.voice_configs[current_speaker]
                    })
                current_speaker = "SPEAKER_B"
                current_text = line.replace("SPEAKER_B:", "").strip()
            elif current_speaker and line:
                current_text += " " + line

        if current_speaker and current_text.strip():
            segments.append({
                'speaker': current_speaker,
                'text': current_text.strip(),
                'voice_id': self.voice_configs[current_speaker]
            })

        logger.debug(f"Parsed {len(segments)} segments: {segments}")
        return segments

    def generate_audio_segment(self, text: str, voice_id: str, speaker_name: str) -> bytes:
        """Generate audio for a single segment.
        Args:
            text (str): The text to convert to speech.
            voice_id (str): The Eleven Labs voice ID for the speaker.
            speaker_name (str): The name of the speaker for logging.
        Returns:
            bytes: The generated audio data in MP3 format.
        Raises:
            RuntimeError: If audio generation fails.
        """
        logger.info(f"Generating audio for {speaker_name}: {text[:50]}...")
        audio_agent = Agent(
            name=f"Audio Generator - {speaker_name}",
            model=Gemini(),
            tools=[
                ElevenLabsTools(
                    api_key=os.getenv("ELEVEN_LABS_API_KEY"),
                    voice_id=voice_id,
                    model_id="eleven_multilingual_v2",
                    target_directory="temp_audio"
                )
            ],
            instructions=[
                "Convert the provided text to speech using the assigned voice.",
                "Generate clear, natural-sounding audio."
            ]
        )
        response = audio_agent.run(f"Convert this text to speech: {text}")
        if response.audio and len(response.audio) > 0:
            audio_data = base64.b64decode(response.audio[0].base64_audio)
            return audio_data
        else:
            logger.error(f"Failed to generate audio for {speaker_name}: {text}")
            return None

    def combine_audio_segments(self, audio_segments: list, output_filename: str) -> str:
        """Combine audio segments with pauses and save as MP3.
        Args:
            audio_segments (list): List of audio data bytes for each segment.
            output_filename (str): The name of the output MP3 file.
        Returns:
            str: The path to the combined audio file.
        Raises:
            RuntimeError: If combining audio segments fails.
        """
        combined = AudioSegment.empty()
        pause = AudioSegment.silent(duration=500)  # 500ms pause
        for i, audio_data in enumerate(audio_segments):
            if audio_data:
                audio_segment = AudioSegment.from_file(BytesIO(audio_data), format="mp3")
                combined += audio_segment
                if i < len(audio_segments) - 1:
                    combined += pause
        os.makedirs("final_podcast", exist_ok=True)
        output_path = os.path.join("final_podcast", output_filename)
        combined.export(output_path, format="mp3")
        logger.info(f"Combined audio saved to {output_path}")
        return output_path

    def run(self, prompt: str) -> RunResponse:
        """
        Executes the multi-source workflow using the routing team.
        Args:
            prompt (str): The input prompt containing URLs, text, or other content.
        Returns:
            RunResponse: The response containing processed content, audio, and any warnings.
        Raises:
            RuntimeError: If the workflow fails to process the input after maximum retries.
        """
        warnings = []
        run_response = RunResponse(content="", audio=None)

        # Step 1: Route to URL Handler and correct with JSON Corrector
        max_retries = 2
        for attempt in range(max_retries + 1):
            url_response = self.url_handler_agent.run(prompt)
            if not url_response or not url_response.content:
                warnings.append(f"Attempt {attempt + 1}: Failed to process URLs: No response from URL Handler.")
                if attempt < max_retries:
                    continue
                return RunResponse(content=f"Failed to process input after {max_retries + 1} attempts. Warnings: {warnings}")

            logger.debug(f"Attempt {attempt + 1}: Raw URL Handler response: {json.dumps(url_response.content, ensure_ascii=False)}")

            corrector_response = self.json_corrector_agent.run(url_response.content)
            logger.debug(f"Attempt {attempt + 1}: JSON Corrector response: {json.dumps(corrector_response.content, ensure_ascii=False)}")

            # Strip Markdown if present and validate JSON structure
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
                return RunResponse(content=f"Failed to process input after {max_retries + 1} attempts due to invalid JSON. Warnings: {warnings}")

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
                f"Route text to Text Processor unless it’s a podcast request."
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

        # Step 5: Check for podcast request
        podcast_keywords = ["podcast", "create podcast", "generate podcast", "make podcast"]
        if any(keyword in remaining_text.lower() for keyword in podcast_keywords):
            logger.debug(f"Processing podcast request with content: {combined_response}")
            # Use remaining_text as topic if no content was processed
            topic = combined_response or remaining_text
            conversation = self.generate_conversation(topic)
            if not conversation:
                run_response.content += "\nFailed to generate podcast conversation."
                logger.error("Failed to generate conversation")
                return run_response

            # Log the generated conversation
            print("✅ Conversation generated successfully")
            segments = self.parse_conversation_segments(conversation)
            if not segments:
                run_response.content += "\nFailed to parse conversation segments."
                logger.error("Failed to parse conversation segments")
                return run_response
            # Generate audio segments for each parsed conversation segment
            print(f"Parsed {len(segments)} conversation segments")
            audio_segments = []
            for i, segment in enumerate(segments):
                print(f"Processing segment {i+1}/{len(segments)}")
                audio_data = self.generate_audio_segment(
                    segment['text'],
                    segment['voice_id'],
                    segment['speaker']
                )
                audio_segments.append(audio_data)

            output_path = self.combine_audio_segments(
                audio_segments,
                f"podcast_{uuid4()}.mp3"
            )
            if output_path:
                logger.info(f"Podcast generated: {output_path}")
            else:
                logger.warning("Failed to generate podcast audio.")

        if warnings:
            logger.warning(f"\n\nWarnings: {warnings}")

        return run_response

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
    serve_playground_app("l5-2:app")