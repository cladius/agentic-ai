# Level 4: Custom RAG Agent with Resume Retrieval (LangGraph, Groq, ChromaDB)

This project demonstrates how to build a Retrieval Augmented Generation (RAG) agent that can answer questions about your resume using Groq's LLM and a custom retrieval tool. The agent uses LangGraph to manage reasoning steps and ChromaDB to store and search resume content.

## What does this project do?
- Loads your resume PDF and splits it into searchable text chunks.
- Stores the chunks as embeddings in a persistent ChromaDB collection.
- Defines a retrieval tool that can search your resume for relevant information.
- Sets up a custom RAG agent using LangGraph, which decides when to use the retrieval tool.
- Visualizes the agent's reasoning process as a state graph.
- Lets you ask questions like "Where did I study?" and get answers from your resume.

## Getting Started

### Install the required packages:
```bash
pip install -r requirements.txt
```

### Set your API key:
In the code, replace `your_groq_api_key_here` with your actual Groq API key:
```python
os.environ["GROQ_API_KEY"] = "your_groq_api_key_here"
```

### Add your resume:
Place your resume PDF in the `RAG/` folder and update the path in the code if needed.

## How to use this project
1. Run the `app.py` script.
2. The script will load your resume, create embeddings, and set up the retrieval tool.
3. The RAG agent will be ready to answer questions about your resume.
4. Try asking questions like "Tell me about projects" or "Where did I study?" and see the agent retrieve answers from your resume.


## Example Output
```
User: Where did I study?
AI: (The agent retrieves and answers based on your resume content)
```
