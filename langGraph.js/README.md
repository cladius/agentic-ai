# 🤖 Agentic AI with LangGraph.js

Welcome to the Agentic_AI-LangGraph.js repository! This is a collection of 5 distinct AI agents, each built using [Node.js](https://nodejs.org/), [LangChain.js](https://js.langchain.com/docs/introduction/), and the [LangGraph.js](https://langchain-ai.github.io/langgraphjs/) library (node/edge based workflows).

These projects are designed to demonstrate a practical progression, starting from a simple conversational bot and building up to a complex, multi-tool RAG (Retrieval-Augmented Generation) pipeline.

## 🛠️ Core Technologies

Across these projects, you will find examples of the following technologies:

- **Node.js**: The runtime environment for all agents.

- **@langchain/langgraph**: The core library for building agentic, graph-based workflows.

- **@langchain/groq**: Provides blazing-fast LLM inference using the Groq API (Llama 3).

- **@langchain/community**: Used for various integrations like vector stores and document loaders.

- **ChromaDB**: The open-source vector store used for RAG agents.

- **Tavily AI**: Integrated for real-time web search capabilities.

- **Tool Usage**: Demonstrations of how agents can use tools for specific tasks (web search, OCR, content creation).

## 🚀 The Agents

This repository contains 5 standalone agents. Each has its own ```README.md``` with specific setup instructions.

**Agent-1**: Basic chat agent
- A foundational, memory-free conversational agent. It demonstrates the simplest possible LangGraph workflow: taking user input, calling an LLM (Groq Llama 3), and returning the response.
- Use-case: single-turn CLI chat with Groq via LangGraph.
- See [Agent-1 documentation](./Agent-1/README.md)

**Agent-2**: Chat Agent with Memory
- An evolution of the first agent, this project integrates ```BufferMemory```. It shows how to maintain conversational history within a LangGraph state, allowing for follow-up questions and context-aware replies.
- Use-case: multi-turn CLI chat with Groq + memory via LangGraph.
- See [Agent-2 documentation](./Agent-2/README.md)

**Agent-3**: Agent with Real-Time Web Search
- This agent introduces tool usage. It intelligently decide whether to answer from its own knowledge or perform a "real-time web search" using the Tavily AI API to get up-to-date information. When queries require current real-time information, the agent invokes Tavily search, summarizes results, then answers.
- Use-case: Conversational agent with web search capabilities.
- See [Agent-3 documentation](./Agent-3/README.md)

**Agent-4**: RAG pipeline with OCR
- A powerful RAG pipeline that can "read" text from images. It uses Optical Character Recognition (OCR) using Tesseract.js to ingest data from user-provided images, embeds (using Hugging Face embeddings) and stores them in a Chroma vector database, and answers questions based on the visual content.
- Use-case: Extract information from resume images and answer questions about them.
- See [Agent-4 documentation](./Agent-4/README.md)

**Agent-5**: Multi-modal RAG Agent with ingestion & processing tools
- The most advanced agent in the collection. It can ingest and process knowledge from multiple sources (PDFs, YouTube videos, webpages, raw text) into a ChromaDB vector store. It then uses a sophisticated router to not only answer questions but also perform higher-level tasks like generating mind maps, writing notes and summaries, or even creating two-voice podcasts (using Google TTS) from the ingested content.
- Use-case: End-to-end RAG system with multi-source ingestion and advanced processing.
- See [Agent-5 documentation](./Agent-5/README.md)

Open each agent's README for full details and environment instructions.

## 🚀 Getting Started

### 1. Prerequisites
- [Node.js (v18+)](https://nodejs.org/) 
- npm
- GROQ_API_KEY (Groq account)
- (Optional) TAVILY_API_KEY — real-time search (Agent-3)
- (Optional) Docker Desktop — required for local Chroma DB (Agents 4 & 5)
- (Optional) Google Cloud account & service account JSON — for podcast TTS (Agent-5)

---

### 2. General Setup & Running
Each agent is a standalone project. To run one:

```bash
# 1. Clone the repository
git clone https://github.com/Mishty-G01/Agentic_AI-LangGraph.js.git

# 2. Navigate to the agent you want to run
cd Agentic_AI-LangGraph.js/Agent-5 # (or Agent-1, Agent-2, etc.)

# 3. Install its dependencies
npm install

# 4. Set up environment variables (see below)

# 5. Run the agent
node index.js
```
Interact with the agent in your terminal. Most agents support an ```exit``` command to quit.

---

### 3. Environment variables 
Create a ```.env``` file in each agent's directory as needed.

- GROQ_API_KEY: Required by **all agents**. Get from [Groq Console](https://console.groq.com/keys).

- TAVILY_API_KEY: Required by **Agent-3** for web search. Get from [Tavily Dashboard](https://app.tavily.com/home).

- gcp-tts.json: Required by **Agent-5** for the podcast tool. (See Agent-5's README for setup).

Example ```.env``` (place in the agent folder you run):

```bash
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here   # Agent-3 only
```
---

### 4. Running Chroma (Agent-4 & Agent-5)
Chroma is used as the local vector DB in Agent-4 and Agent-5. Run via Docker:

```bash
# 1. make sure Docker Desktop is open and running

# 2. Pull the Chroma image
docker pull chromadb/chroma

# 3. Run the Chroma container
docker run -p 8000:8000 chromadb/chroma
```
If using remote Chroma, adapt vectorstore client config in the agent code.

--- 

### Resources
#### 🎥 **Demo**
Check out a demo video of the project [here](https://github.com/user-attachments/assets/caf41d65-56b2-4cf3-a3fd-9246a84ac1f5)

#### **Documentation**
Check out the [LangGraph_documentation](https://github.com/user-attachments/files/23551319/LangGraph_Report_MishtyGupta.pdf)

## Acknowledgements
This collection of projects was built while learning the powerful agentic framework provided by [LangGraph.js](https://langchain-ai.github.io/langgraphjs/) and the high-speed inference from Groq.
