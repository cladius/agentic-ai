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

## Architecture

The application is built on a state-driven graph. The **Planner Agent** acts as the brain, determining user intent and routing the 'AgentState' through specialized nodes.



### Agent Roles
| Agent | Responsibility |
| :--- | :--- |
| **Planner** | Classifies intent (QnA, Ingest, Podcast) using structured JSON output. |
| **YouTube Ingester** | Processes YouTube URLs using "YoutubeLoader" and chunks text. |
| **Web Ingester** | Scrapes URLs using "WebBaseLoader" and "BeautifulSoup". |
| **QnA Agent** | Performs similarity searches in the FAISS index to provide context. |
| **Podcast Agent** | Scriptwriting via LLM and Audio synthesis via Eleven Labs API. |
| **MindMap Agent** | Synthesizes content into hierarchical Mermaid diagrams. |

---

## Prerequisites

* **Python 3.10+**
* **Groq API Key**: Required for LLM inference
* **Eleven Labs API Key**: Required for professional-grade Text-to-Speech translation
* **HuggingFace**: Required for using Embedding Model

---

## ⚙️ Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/cladius/agentic-ai.git
    cd langgraph
    ```

2.  **Install dependencies**:
    ```bash
    pip install langchain langchain-groq langgraph faiss-cpu sentence-transformers beautifulsoup4 youtube-transcript-api elevenlabs pydantic
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
* Refer to the [Groq Cloud](https://console.groq.com/home) to get API Keys
* [Elevenlabs](https://elevenlabs.io/api) for text-speech conversion

