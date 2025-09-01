# LangGraph NotebookLM Clone
# A CLI-based application with multiple agents for content ingestion and podcast generation

import os
import sys
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import faiss
import numpy as np
from pathlib import Path

# LangChain imports
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader, YoutubeLoader
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain.schema import Document
from langchain.embeddings.base import Embeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

# LangGraph imports
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

# Additional imports
import requests
from bs4 import BeautifulSoup
import youtube_transcript_api
import subprocess
from pydantic import BaseModel, Field
from typing import Literal


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class IntentType(Enum):
    YOUTUBE_INGEST = "youtube_ingest"
    WEBPAGE_INGEST = "webpage_ingest"
    QNA = "qna"
    PODCAST_CREATE = "podcast_create"
    MINDMAP_CREATE = "mindmap_create"
    UNKNOWN = "unknown"


@dataclass
class Config:
    groq_api_key: str
    elevenlabs_api_key: str
    embeddings_model: str
    vectorstore_path: str = "./vectorstore"
    chunk_size: int = 1000
    chunk_overlap: int = 200


class CustomEmbeddings(Embeddings):
    """Custom embeddings class for using HuggingFaceEmbeddings"""
    
    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.hf_embedder = HuggingFaceEmbeddings(model_name=model)
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.hf_embedder.embed_documents(texts)
    
    def embed_query(self, text: str) -> List[float]:
        return self.hf_embedder.embed_query(text)


class AgentState(TypedDict):
    user_input: str
    intent: str
    content: Optional[str]
    url: Optional[str]
    query: Optional[str]
    topic: Optional[str]
    retrieved_content: Optional[List[str]]
    transcript: Optional[str]
    audio_file: Optional[str]
    error: Optional[str]
    response: Optional[str]


class IntentClassification(BaseModel):
    """Structured output for intent classification"""
    intent: Literal["YOUTUBE_INGEST", "WEBPAGE_INGEST", "QNA", "PODCAST_CREATE", "MINDMAP_CREATE", "UNKNOWN"] = Field(
        description="The classified intent of the user input"
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0 for the classification",
        ge=0.0,
        le=1.0
    )
    reasoning: str = Field(
        description="Brief explanation of why this intent was chosen"
    )
    extracted_url: Optional[str] = Field(
        description="Any URL found in the input, null if none",
        default=None
    )
    extracted_topic: Optional[str] = Field(
        description="Topic extracted for podcast creation, null if not applicable",
        default=None
    )


class PlannerAgent:
    """Analyzes user input and determines intent using LLM with structured output"""
    
    def __init__(self, llm: ChatGroq):
        self.llm = llm
    
    def analyze_intent_structured(self, user_input: str) -> tuple[IntentType, Optional[str], Optional[str]]:
        """Analyze user input with structured output"""
        try:
            intent_prompt = f"""
Analyze the following user input and classify it with structured reasoning.

Available intents:
1. YOUTUBE_INGEST - User wants to process/ingest a YouTube video
2. WEBPAGE_INGEST - User wants to process/ingest a webpage or URL  
3. QNA - User is asking a question about previously ingested content
4. PODCAST_CREATE - User wants to create an audio podcast
5. MINDMAP_CREATE - User wants to create a mind map
6. UNKNOWN - Intent doesn't match any category

User Input: "{user_input}"

Provide:
- intent: The classified intent
- confidence: How confident you are (0.0-1.0)
- reasoning: Why you chose this intent
- extracted_url: Any URL found in the input
- extracted_topic: Topic for podcast creation (if applicable)

Examples:
Input: "Add this YouTube video https://youtube.com/watch?v=123"
Output: {{"intent": "YOUTUBE_INGEST", "confidence": 0.95, "reasoning": "User explicitly wants to add/process a YouTube video with URL provided", "extracted_url": "https://youtube.com/watch?v=123", "extracted_topic": null}}

Input: "What did the articles say about climate change?"
Output: {{"intent": "QNA", "confidence": 0.9, "reasoning": "User is asking a question about previously ingested content", "extracted_url": null, "extracted_topic": null}}

Respond with valid JSON matching the structure above. Do NOT include any additional text or explanations. ONLY return the JSON object"""
            
            response = self.llm.invoke(intent_prompt)
            
            # Try to parse JSON response
            try:
                import json
                result_data = json.loads(response.content.strip())

                # Log the raw response for debugging
                logger.info(f"Raw structured response: {result_data}")

                classification = IntentClassification(**result_data)
                
                # Convert to IntentType enum
                intent_mapping = {
                    "YOUTUBE_INGEST": IntentType.YOUTUBE_INGEST,
                    "WEBPAGE_INGEST": IntentType.WEBPAGE_INGEST,
                    "QNA": IntentType.QNA,
                    "PODCAST_CREATE": IntentType.PODCAST_CREATE,
                    "MINDMAP_CREATE": IntentType.MINDMAP_CREATE,
                    "UNKNOWN": IntentType.UNKNOWN
                }
                
                intent = intent_mapping.get(classification.intent, IntentType.UNKNOWN)
                logger.info(f"Intent classified: {intent.value} (confidence: {classification.confidence})")
                logger.info(f"Reasoning: {classification.reasoning}")
                
                return intent, classification.extracted_url, classification.extracted_topic
                
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to parse structured response, falling back to simple classification: {e}")
                return self.analyze_intent(user_input), None, None
                
        except Exception as e:
            logger.error(f"Error in structured intent analysis: {str(e)}")
            return self.analyze_intent(user_input), None, None
    
    def analyze_intent(self, user_input: str) -> IntentType:
        """Analyze user input to determine intent using LLM"""
        try:
            intent_prompt = f"""
Analyze the following user input and classify it into one of these intents:

1. YOUTUBE_INGEST - User wants to ingest/process a YouTube video (extract transcript, add to knowledge base)
2. WEBPAGE_INGEST - User wants to ingest/process a webpage or URL (extract content, add to knowledge base)  
3. QNA - User is asking a question about previously ingested content
4. PODCAST_CREATE - User wants to create an audio podcast about a specific topic
5. MINDMAP_CREATE - User wants to create a mind map
6. UNKNOWN - Intent doesn't match any of the above categories

User Input: "{user_input}"

You must respond with ONLY the intent name (YOUTUBE_INGEST, WEBPAGE_INGEST, QNA, PODCAST_CREATE, MINDMAP_CREATE or UNKNOWN).

Examples:
- "Please add this YouTube video to my knowledge base: https://youtube.com/watch?v=123" → YOUTUBE_INGEST
- "Can you process this article for me? https://example.com/article" → WEBPAGE_INGEST
- "What did the video say about machine learning?" → QNA
- "Generate a podcast discussion about climate change" → PODCAST_CREATE
- "Hello there" → UNKNOWN

Intent:"""
            
            response = self.llm.invoke(intent_prompt)
            intent_str = response.content.strip().upper()
            
            # Map string response to IntentType enum
            intent_mapping = {
                "YOUTUBE_INGEST": IntentType.YOUTUBE_INGEST,
                "WEBPAGE_INGEST": IntentType.WEBPAGE_INGEST,
                "QNA": IntentType.QNA,
                "PODCAST_CREATE": IntentType.PODCAST_CREATE,
                "UNKNOWN": IntentType.UNKNOWN
            }
            
            return intent_mapping.get(intent_str, IntentType.UNKNOWN)
            
        except Exception as e:
            logger.error(f"Error in intent analysis: {str(e)}")
            return IntentType.UNKNOWN
    
    def extract_url_from_input(self, user_input: str) -> Optional[str]:
        """Extract URL from user input using LLM"""
        try:
            url_prompt = f"""
Extract any URL from the following text. If there's no URL, respond with "NONE".

Text: "{user_input}"

Examples:
- "Check out this video https://youtube.com/watch?v=abc123" → https://youtube.com/watch?v=abc123
- "Process this page: www.example.com/article" → www.example.com/article  
- "What do you think about AI?" → NONE

URL:"""
            
            response = self.llm.invoke(url_prompt)
            url = response.content.strip()
            
            if url == "NONE" or not url:
                return None
                
            # Add https:// if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
                
            return url
            
        except Exception as e:
            logger.error(f"Error extracting URL: {str(e)}")
            # Fallback to regex
            import re
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            urls = re.findall(url_pattern, user_input)
            return urls[0] if urls else None
    
    def extract_topic_from_input(self, user_input: str) -> str:
        """Extract topic for podcast creation using LLM"""
        try:
            topic_prompt = f"""
Extract the main topic or subject for podcast creation from the following user input.
Return only the topic/subject without any additional text.

User Input: "{user_input}"

Examples:
- "Create a podcast about artificial intelligence and machine learning" → artificial intelligence and machine learning
- "Generate an audio discussion on climate change impacts" → climate change impacts
- "Make a podcast on the history of space exploration" → history of space exploration
- "Create a podcast" → general discussion

Topic:"""
            
            response = self.llm.invoke(topic_prompt)
            topic = response.content.strip()
            
            return topic if topic else "general discussion"
            
        except Exception as e:
            logger.error(f"Error extracting topic: {str(e)}")
            # Fallback to simple extraction
            words = user_input.split()
            topic_start = -1
            for i, word in enumerate(words):
                if word.lower() in ["on", "about", "topic", "regarding", "concerning"]:
                    topic_start = i + 1
                    break
            
            if topic_start != -1 and topic_start < len(words):
                return " ".join(words[topic_start:])
            return "general discussion"


class YouTubeIngesterAgent:
    """Handles YouTube video transcript ingestion"""
    
    def __init__(self, embeddings: CustomEmbeddings, vectorstore_path: str):
        self.embeddings = embeddings
        self.vectorstore_path = vectorstore_path
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    def ingest_youtube_video(self, url: str) -> bool:
        """Ingest YouTube video transcript"""
        try:
            logger.info(f"Ingesting YouTube video: {url}")
            
            # Load YouTube transcript
            loader = YoutubeLoader.from_youtube_url(url)
            documents = loader.load()

            # Print each document's content for debugging
            for doc in documents:
                logger.info(f"Document content: {doc.page_content}")
            
            if not documents:
                logger.error("No transcript found for the video")
                return False
            
            # Split documents
            splits = self.text_splitter.split_documents(documents)
            
            # Load or create vectorstore
            vectorstore = self._load_or_create_vectorstore()
            
            # Add documents to vectorstore
            vectorstore.add_documents(splits)
            
            # Save vectorstore
            vectorstore.save_local(self.vectorstore_path)
            
            logger.info(f"Successfully ingested {len(splits)} chunks from YouTube video")
            return True
            
        except Exception as e:
            logger.error(f"Error ingesting YouTube video: {str(e)}")
            return False
    
    def _load_or_create_vectorstore(self):
        """Load existing vectorstore or create new one"""
        vectorstore_path = Path(self.vectorstore_path)
        if vectorstore_path.exists():
            return FAISS.load_local(self.vectorstore_path, self.embeddings, allow_dangerous_deserialization=True)
        else:
            # Create empty vectorstore
            sample_doc = Document(page_content="sample", metadata={})
            vectorstore = FAISS.from_documents([sample_doc], self.embeddings)
            return vectorstore


class WebpageIngesterAgent:
    """Handles webpage content ingestion"""
    
    def __init__(self, embeddings: CustomEmbeddings, vectorstore_path: str):
        self.embeddings = embeddings
        self.vectorstore_path = vectorstore_path
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    def ingest_webpage(self, url: str) -> bool:
        """Ingest webpage content"""
        try:
            logger.info(f"Ingesting webpage: {url}")
            
            loader = WebBaseLoader(url)
            documents = loader.load()
            
            if not documents:
                logger.error("No content found on the webpage")
                return False
            
            # Split documents
            splits = self.text_splitter.split_documents(documents)
            
            # Load or create vectorstore
            vectorstore = self._load_or_create_vectorstore()
            
            # Add documents to vectorstore
            vectorstore.add_documents(splits)
            
            # Save vectorstore
            vectorstore.save_local(self.vectorstore_path)
            
            logger.info(f"Successfully ingested {len(splits)} chunks from webpage")
            return True
            
        except Exception as e:
            logger.error(f"Error ingesting webpage: {str(e)}")
            return False
    
    def _load_or_create_vectorstore(self):
        """Load existing vectorstore or create new one"""
        vectorstore_path = Path(self.vectorstore_path)
        if vectorstore_path.exists():
            return FAISS.load_local(self.vectorstore_path, self.embeddings, allow_dangerous_deserialization=True)
        else:
            sample_doc = Document(page_content="sample", metadata={})
            vectorstore = FAISS.from_documents([sample_doc], self.embeddings)
            return vectorstore


class QnAAgent:
    """Handles question answering using retrieved content"""
    
    def __init__(self, llm: ChatGroq, embeddings: CustomEmbeddings, vectorstore_path: str):
        self.llm = llm
        self.embeddings = embeddings
        self.vectorstore_path = vectorstore_path
    
    def answer_question(self, question: str) -> str:
        """Answer question using retrieved content"""
        try:
            logger.info(f"Answering question: {question}")
            
            # Load vectorstore
            vectorstore_path = Path(self.vectorstore_path)
            if not vectorstore_path.exists():
                return "No content has been ingested yet. Please ingest some content first."
            
            vectorstore = FAISS.load_local(self.vectorstore_path, self.embeddings, allow_dangerous_deserialization=True)
            
            # Retrieve relevant documents
            docs = vectorstore.similarity_search(question, k=5)
            
            if not docs:
                return "I couldn't find relevant information to answer your question."
            
            # Combine retrieved content
            context = "\n\n".join([doc.page_content for doc in docs])
            
            # Generate answer
            prompt = f"""Based on the following context, please answer the question:

Context:
{context}

Question: {question}

Answer:"""
            
            response = self.llm.invoke(prompt)
            return response.content
            
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            return f"Error answering question: {str(e)}"
    
    def retrieve_content_for_topic(self, topic: str) -> List[str]:
        """Retrieve content related to a topic"""
        try:
            vectorstore_path = Path(self.vectorstore_path)
            if not vectorstore_path.exists():
                return []
            
            vectorstore = FAISS.load_local(self.vectorstore_path, self.embeddings, allow_dangerous_deserialization=True)
            docs = vectorstore.similarity_search(topic, k=10)
            
            return [doc.page_content for doc in docs]
            
        except Exception as e:
            logger.error(f"Error retrieving content: {str(e)}")
            return []


class PodcastTranscriptAgent:
    """Generates podcast transcript from retrieved content"""
    
    def __init__(self, llm: ChatGroq):
        self.llm = llm
    
    def generate_transcript(self, topic: str, content: List[str]) -> str:
        """Generate 2-person podcast transcript"""
        try:
            logger.info(f"Generating podcast transcript for topic: {topic}")
            
            if not content:
                return "Not enough content to generate podcast."
            
            # Combine content
            combined_content = "\n\n".join(content[:5])  # Use top 5 chunks
            
            prompt = f"""Create a 2-person podcast transcript about "{topic}" based on the following content:

Content:
{combined_content}

Instructions:
- Create a natural conversation between Host and Expert
- Make it engaging and informative
- Include transitions and natural dialogue
- Length: approximately 5-10 minutes of content
- Do NOT use markdown. Do NOT print anything other than the transcript.
- Each line 
- Format as:
Host: [dialogue]
Expert: [dialogue]

Transcript:"""
            
            response = self.llm.invoke(prompt)

            #Print the generated transcript for debugging
            logger.info(f"Generated transcript: {response.content.strip()}")
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error generating transcript: {str(e)}")
            return f"Error generating transcript: {str(e)}"


class PodcastAgent:
    """Converts transcript to audio using Eleven Labs"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io/v1"
    
    def generate_audio(self, transcript: str, output_file: str = "podcast.mp3") -> Optional[str]:
        """Generate audio from transcript"""
        try:
            logger.info("Generating audio from transcript")
            
            # Parse transcript to separate speakers
            lines = transcript.split('\n')
            audio_segments = []
            
            for line in lines:
                if line.strip():
                    if line.startswith('Host:'):
                        text = line.replace('Host:', '').strip()
                        voice_id = "21m00Tcm4TlvDq8ikWAM"  # Default voice
                    elif line.startswith('Expert:'):
                        text = line.replace('Expert:', '').strip()
                        voice_id = "AZnzlk1XvdvUeBnXmlld"  # Different voice
                    else:
                        continue
                    
                    if text:
                        audio_data = self._text_to_speech(text, voice_id)
                        if audio_data:
                            audio_segments.append(audio_data)
            
            if audio_segments:
                # Combine audio segments (simplified approach)
                with open(output_file, 'wb') as f:
                    for segment in audio_segments:
                        f.write(segment)
                
                logger.info(f"Audio generated: {output_file}")
                return output_file
            else:
                logger.error("No audio segments generated")
                return None
                
        except Exception as e:
            logger.error(f"Error generating audio: {str(e)}")
            return None
    
    def _text_to_speech(self, text: str, voice_id: str) -> Optional[bytes]:
        """Convert text to speech using Eleven Labs API"""
        try:
            url = f"{self.base_url}/text-to-speech/{voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"TTS API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error in text-to-speech: {str(e)}")
            return None

class MindMapAgent:
    """Generates mindmap in mermaid.js syntax from retrieved content"""
    
    def __init__(self, llm: ChatGroq):
        self.llm = llm
    
    def generate_mindmap(self, topic: str, content: List[str]) -> str:
        """Generate mindmap for a given topic based on retrieved content in mermaid.js syntax"""
        try:
            logger.info(f"Generating mindmap for topic: {topic}")
            
            if not content:
                return "Not enough content to generate mindmap."
            
            # Combine content
            combined_content = "\n\n".join(content[:5])  # Use top 5 chunks

            prompt = f"""Create a mindmap for "{topic}" based on the following content:

Content:
{combined_content}

Instructions:
- Output in mermaid.js syntax
- Use clear hierarchical structure
- Include main topic and subtopics
- Do NOT use markdown. Do NOT print anything other than the mindmap code.
- Format as:
```mermaid
mindmap
  root((Main Topic))
    subtopic1((Subtopic 1))
    subtopic2((Subtopic 2))
```
- Each node should be a clear concept or idea
- Use concise labels for nodes

Output:"""
            
            response = self.llm.invoke(prompt)

            logger.info(f"Generated mindmap.")
            
            if not response.content.strip():
                return "Failed to generate mindmap. Please try again."
            return response.content
            
        except Exception as e:
            logger.error(f"Error generating mindmap: {str(e)}")
            return f"Error generating mindmap: {str(e)}"

class NotebookLMApp:
    """Main application class orchestrating all agents"""
    
    def __init__(self, config: Config):
        self.config = config
        
        # Initialize LLM
        self.llm = ChatGroq(api_key=config.groq_api_key, model_name="llama3-8b-8192")
        
        # Initialize embeddings
        self.embeddings = CustomEmbeddings(config.embeddings_model)
        
        # Initialize agents
        self.planner = PlannerAgent(self.llm)
        self.youtube_ingester = YouTubeIngesterAgent(self.embeddings, config.vectorstore_path)
        self.webpage_ingester = WebpageIngesterAgent(self.embeddings, config.vectorstore_path)
        self.qna_agent = QnAAgent(self.llm, self.embeddings, config.vectorstore_path)
        self.transcript_agent = PodcastTranscriptAgent(self.llm)
        self.podcast_agent = PodcastAgent(config.elevenlabs_api_key)
        self.mindmap_agent = MindMapAgent(self.llm)
        
        # Initialize LangGraph
        self.graph = self._create_graph()

    def get_graph(self) -> StateGraph:
        """Get the LangGraph workflow"""
        return self.graph
    
    def _create_graph(self) -> StateGraph:
        """Create LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("youtube_ingester", self._youtube_ingester_node)
        workflow.add_node("webpage_ingester", self._webpage_ingester_node)
        workflow.add_node("qna", self._qna_node)
        workflow.add_node("podcast_transcript", self._podcast_transcript_node)
        workflow.add_node("podcast_audio", self._podcast_audio_node)
        workflow.add_node("mindmap_create", self._generate_mindmap_node)
        workflow.add_node("respond", self._respond_node)
        
        # Set entry point
        workflow.set_entry_point("planner")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "planner",
            self._route_intent,
            {
                "youtube_ingest": "youtube_ingester",
                "webpage_ingest": "webpage_ingester",
                "qna": "qna",
                "podcast_create": "qna",  # First retrieve content
                "mindmap_create": "qna",  # First retrieve content
                "unknown": "respond"
            }
        )
        
        # Add edges to respond
        workflow.add_edge("youtube_ingester", "respond")
        workflow.add_edge("webpage_ingester", "respond")
        workflow.add_edge("mindmap_create", "respond")
        workflow.add_edge("podcast_transcript", "podcast_audio")
        workflow.add_edge("podcast_audio", "respond")
        workflow.add_edge("respond", END)
        
        # Add conditional edge from qna for podcast creation
        workflow.add_conditional_edges(
            "qna",
            self._route_intent,
            {
                "podcast_create": "podcast_transcript",
                "qna": "respond",
                "mindmap_create": "mindmap_create"
            }
        )
        
        return workflow.compile()
    
    def _planner_node(self, state: AgentState) -> AgentState:
        """Planner node with structured intent analysis"""
        # Use structured analysis first
        intent, extracted_url, extracted_topic = self.planner.analyze_intent_structured(state["user_input"])
        state["intent"] = intent.value
        
        # Use extracted values or fall back to individual extraction methods
        if intent in [IntentType.YOUTUBE_INGEST, IntentType.WEBPAGE_INGEST]:
            state["url"] = extracted_url or self.planner.extract_url_from_input(state["user_input"])
        elif intent in [IntentType.PODCAST_CREATE, IntentType.MINDMAP_CREATE]:
            state["topic"] = extracted_topic or self.planner.extract_topic_from_input(state["user_input"])
        elif intent == IntentType.QNA:
            state["query"] = state["user_input"]
        
        return state
    
    def _youtube_ingester_node(self, state: AgentState) -> AgentState:
        """YouTube ingester node"""
        if state.get("url"):
            success = self.youtube_ingester.ingest_youtube_video(state["url"])
            state["response"] = "YouTube video ingested successfully!" if success else "Failed to ingest YouTube video."
        else:
            state["response"] = "No YouTube URL provided."
        return state
    
    def _webpage_ingester_node(self, state: AgentState) -> AgentState:
        """Webpage ingester node"""
        if state.get("url"):
            success = self.webpage_ingester.ingest_webpage(state["url"])
            state["response"] = "Webpage ingested successfully!" if success else "Failed to ingest webpage."
        else:
            state["response"] = "No URL provided."
        return state
    
    def _qna_node(self, state: AgentState) -> AgentState:
        """QnA node"""

        # If the intent is podcast creation OR mindmap creation,
        # retrieve content first
        if state["intent"] in ["podcast_create", "mindmap_create"]:
            # Retrieve content for podcast
            content = self.qna_agent.retrieve_content_for_topic(state.get("topic", ""))
            state["retrieved_content"] = content
        else:
            # Answer question
            answer = self.qna_agent.answer_question(state.get("query", ""))
            state["response"] = answer
        return state
    
    def _podcast_transcript_node(self, state: AgentState) -> AgentState:
        """Podcast transcript node"""
        topic = state.get("topic", "general topic")
        content = state.get("retrieved_content", [])
        transcript = self.transcript_agent.generate_transcript(topic, content)
        state["transcript"] = transcript
        return state
    
    def _generate_mindmap_node(self, state: AgentState) -> AgentState:
        """Generate mindmap node"""
        topic = state.get("topic", "general topic")
        content = state.get("retrieved_content", [])
        mindmap = self.mindmap_agent.generate_mindmap(topic, content)
        state["response"] = mindmap
        return state

    def _podcast_audio_node(self, state: AgentState) -> AgentState:
        """Podcast audio node"""
        transcript = state.get("transcript", "")
        if transcript:
            audio_file = self.podcast_agent.generate_audio(transcript)
            if audio_file:
                state["response"] = f"Podcast created successfully! Audio file: {audio_file}"
                state["audio_file"] = audio_file
            else:
                state["response"] = "Failed to generate audio for podcast."
        else:
            state["response"] = "No transcript available for audio generation."
        return state
    
    def _respond_node(self, state: AgentState) -> AgentState:
        """Final response node"""
        if not state.get("response"):
            state["response"] = "I'm not sure how to help with that. Please try rephrasing your request."
        return state
    
    def _route_intent(self, state: AgentState) -> str:
        """Route based on detected intent"""
        return state["intent"]
    
    def run_cli(self):
        """Run the CLI interface"""
        print("🎙️ Welcome to NotebookLM Clone!")
        print("Type 'exit' to quit, 'help' for commands")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("\n💬 You: ").strip()
                
                if user_input.lower() == 'exit':
                    print("👋 Goodbye!")
                    break
                elif user_input.lower() == 'help':
                    self._show_help()
                    continue
                elif not user_input:
                    continue
                
                # Process user input through LangGraph
                state = {"user_input": user_input}
                result = self.graph.invoke(state)
                
                print(f"\n🤖 Assistant: {result['response']}")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error in CLI: {str(e)}")
                print(f"\n❌ Error: {str(e)}")
    
    def _show_help(self):
        """Show help information"""
        help_text = """
📖 Available Commands:

🎥 YouTube Ingestion:
   "Ingest this YouTube video: [URL]"

🌐 Webpage Ingestion:
   "Ingest this URL: [URL]"

❓ Question Answering:
   Ask any question about ingested content

🎙️ Podcast Creation:
   "Create an audio podcast on topic [TOPIC]"

📋 Other:
   'help' - Show this help
   'exit' - Quit the application
        """
        print(help_text)

def load_config() -> Config:
    """Load configuration from environment variables"""
    groq_api_key = os.getenv("GROQ_API_KEY")
    elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
    embeddings_model = os.getenv("EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable is required")
    if not elevenlabs_api_key:
        raise ValueError("ELEVENLABS_API_KEY environment variable is required")
    
    return Config(
        groq_api_key=groq_api_key,
        elevenlabs_api_key=elevenlabs_api_key,
        embeddings_model=embeddings_model
    )


def main():
    """Main entry point"""
    try:
        config = load_config()
        app = NotebookLMApp(config)
        app.run_cli()
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

def get_graph() -> StateGraph:
    """Get the LangGraph workflow"""
    config = load_config()
    app = NotebookLMApp(config)
    return app.get_graph()

if __name__ == "__main__":
    main()
