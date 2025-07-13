# Pydantic AI Agents Exploration - Git Repository

## Welcome to My Pydantic AI Journey!

This Git repository is my playground to learn and build smart “agents” using the **Pydantic AI framework**. I’m a beginner exploring how to create agents that can answer questions, remember conversations, search the web, store data, and mimic tools like Google NotebookLM. I’ll work through **Levels 1 to 5**, adding new features step by step. This README explains what Pydantic AI is, outlines my plan for each level, and shows how my code is organized. Each level has its own folder with a file, README, flow diagram, and output screenshots to guide you through the process!

---

## What is Pydantic AI?

Pydantic AI is a Python library that helps me build intelligent agents. It:
- Ensures my inputs (like questions or text) are correct and safe.
- Organizes tasks by sending them to the right agent.
- Uses a smart language model (like Google Gemini API) to generate answers.

**Think of it as a helpful assistant that keeps my agents working together smoothly!**

---

## Project Purpose and Levels

I’m building a system with agents to handle different tasks. For each level, I’ll create a folder for each level and a `README.md` with a flow diagram to show how it works. Here’s my plan:

### Level 1: Basic
| **Goal**            | Build a simple “Hello World” agent that answers questions using a language model (LLM). |
|----------------------|---------------------------------------------------------------|
| **What I’ll do**     | Create a single agent (no tools) to respond to basic queries.  |

### Level 2: Conversational Memory
| **Goal**            | Add memory to agents so they remember past conversations.      |
|----------------------|---------------------------------------------------------------|
| **What I’ll do**     | Build an agent that uses conversation history to give better answers. |

### Level 3: Tools
| **Goal**            | Add web search (e.g., Google Search) to an agent, like Perplexity. |
|----------------------|---------------------------------------------------------------|
| **What I’ll do**     | Integrate a tool to fetch the latest information and provide relevant answers. |

### Level 4: Vector Store
| **Goal**            | Create a vector store (e.g., for a Compiler Design book), vectorize a resume, and use OCR to read scans. |
|----------------------|---------------------------------------------------------------|
| **What I’ll do**     | Build agents to store data, extract resume info, and process scanned documents. |

### Level 5: Multi-Agent (Notebook LM Mimic)
| **Goal**            | Build a multi-agent, multi-tool system (PDFs, YouTube URLs, web pages, text, images) to mimic Google NotebookLM with mindmaps and podcasts. |
|----------------------|---------------------------------------------------------------|
| **What I’ll do**     | Create planner agents (PDFs, YouTube URLs, web pages, text, images, mindmaps, podcasts) that call and make all the agents perform their respective tasks. |

---

## Getting Started as a Beginner

### Set Up Your Computer
```plaintext
- Install Python 3.8 or higher from python.org.
- Install required tools:
  pip install pydantic pydantic-ai chromadb logfire python-dotenv Pillow requests
- Install Graphviz (for mindmaps) from graphviz.org and add to PATH.
- Install FFmpeg (for podcasts) from ffmpeg.org and note its path.
- Install Tesseract-OCR (for Level 4 OCR) from github.com/tesseract-ocr and add to PATH.
```

### Create a .env File
```plaintext
In the project folder, make a .env file:
GEMINI_API_KEY=your_gemini_api_key
LOGFIRE_TOKEN=your_logfire_token
ELEVENLABS_API_KEY=your_elevenlabs_api_key
FFMPEG_PATH=your_ffmpeg_path
```
**Get API keys from your guide or sign up (e.g., Google Gemini, ElevenLabs).**

### Explore the Levels
```plaintext
- Go through all the level folders for code and README file details, descriptions, flowcharts, and output screenshots.
```

---

This repo is my step-by-step adventure with Pydantic AI. Let’s create something great together!
