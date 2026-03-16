# Level5 - LangGraph NotebookLM Clone

A powerful, multi-agent CLI application that mimics the core features of Google's NotebookLM. Built using **LangGraph**, this project orchestrates specialized agents to handle content ingestion, RAG-based Q&A, and automated podcast production.



## Features

* **Smart Ingestion**: 
    * **YouTube**: Automatically extracts transcripts and indexes them for retrieval.
    * **Webpages**: Scrapes and chunks web content using "WebBaseLoader".
* **Intelligent Q&A**: Uses a **FAISS** vectorstore and RAG (Retrieval-Augmented Generation) to answer questions based strictly on your context.
* **Podcast Generation**:
    * **Scripting**: Generates a natural, two-person (Host & Expert) dialogue.
    * **Audio**: Converts the script into high-quality audio using **Eleven Labs** with distinct, realistic voices.
* **Visual Mindmaps**: Generates **Mermaid.js** syntax to visualize the hierarchical structure of your "notebook."
* **Structured Intent Analysis**: Powered by Llama 3 via **Groq** for lightning-fast reasoning and routing.

---

## Agent Summary 

### Planner Agent
The application is built on a state-driven graph. The **Planner Agent** acts as the brain, determining user intent and routing the 'AgentState' through specialized nodes.
**Role**: Classifies user intent and routes the shared state through the right agent pipeline.

**Key Responsibilities**:
* Interpret user input into intents (Ingest, QnA, Podcast, MindMap).
* Ensure preconditions are met (e.g., content ingested before QA).
* Dispatch the 'AgentState' to the appropriate agent.
* Report success/failure back to the user.

**Primary Tools**:
* Groq-based intent classification.
* LangGraph state transitions and agent invocation.

---

### YouTube Ingester Agent
**Role**: Ingest YouTube video transcripts and index them for retrieval.

**Key Responsibilities**:
* Accept and validate YouTube URLs.
* Extract transcripts via 'YoutubeLoader'.
* Chunk text and store embeddings in FAISS.

**Primary Tools**:
* 'YoutubeLoader', HuggingFace embeddings, FAISS.

---

### Web Ingester Agent
**Role**: Scrape and index web page content for retrieval.

**Key Responsibilities**:
* Fetch and clean HTML content.
* Chunk and embed text.
* Store embeddings in FAISS.

**Primary Tools**:
* 'WebBaseLoader' + 'BeautifulSoup', HuggingFace embeddings, FAISS.

---

### QnA Agent
**Role**: Answer questions using retrieved context from the FAISS index.

**Key Responsibilities**:
* Perform similarity search against FAISS.
* Build a prompt with retrieved context.
* Generate grounded answers via Groq.

**Primary Tools**:
* FAISS similarity search, Groq LLM.

---

### Podcast Agent
**Role**: Generate a conversational script and synthesize audio.

**Key Responsibilities**:
* Generate a Host/Expert script from a prompt.
* Use Eleven Labs to synthesize audio for each voice.

**Primary Tools**:
* Groq LLM, Eleven Labs TTS.

---

### MindMap Agent
**Role**: Generate Mermaid.js mindmap syntax from ingested content.

**Key Responsibilities**:
* Extract structure and relationships from content.
* Output Mermaid syntax for visualization.

**Primary Tools**:
* Groq LLM analysis, Mermaid formatting logic.


---

## Prerequisites

* **Python 3.10+**
* **Groq API Key**: Required for LLM inference
* **Eleven Labs API Key**: Required for professional-grade Text-to-Speech translation
* **HuggingFace**: Required for using Embedding Model

---

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/cladius/agentic-ai.git
    cd langgraph
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure API Keys**:
    Ensure your keys are set in your environment or passed to the "Config" dataclass:
    ```bash
    export GROQ_API_KEY='your_groq_api_key'
    export ELEVENLABS_API_KEY='your_elevenlabs_api_key'
    ```

---

## Usage

Run the application:
```bash
python level5.py
```
Follow the CLI instructions, ingest the data(webpage url or youtube video link) and ask questions, generate podcasts or mindmaps to test the application.

### References
- Refer to the [Groq Cloud](https://console.groq.com/home) to get API Keys
- [Elevenlabs](https://elevenlabs.io/api) for text-speech conversion
- For detailed descriptions of each level, visit the [Agentic AI Sample Problem](http://github.com/cladius/agentic-ai/blob/master/sample_problem.md).
- For a deep dive on Agentic AI, here's our book - [Agentic AI Demystified: Master the essentials](https://amzn.in/d/02J8fOUV).
- Get your Free Chapter on Agentic AI [here](https://cladiusfernando.com/learn-agentic-ai/).
