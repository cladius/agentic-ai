# Level 1: Hello World Agent using Pydantic AI & Gemini

## 📌 Overview
This project implements a basic “Hello World” agent using [pydantic-ai]

## 🎯 Features
- Simple user-agent interaction via CLI
- Gemini-powered response generation
- Pydantic schemas for input/output validation
- Logging and performance tracing with `logfire`
- .env-based configuration for API keys

## 🧰 Requirements

- Python 3.8+
- Required packages:
  - `pydantic`
  - `pydantic-ai`
  - `google-generativeai`
  - `logfire`
  - `python-dotenv`

## ⚙️ How It Works

Level 1 agent works by accepting a user's question through the command-line interface.
The input is validated using Pydantic models, then sent to Google's Gemini 1.5 Flash model for processing.
The response is returned as a short, clear sentence. pydantic-ai helps structure the agent's logic by defining clean input/output models and managing how data flows between the user, the agent, and the LLM. 
Logging and tracing are handled by logfire for better observability and debugging.

## Flow Diagram 

+------------------+
|   User Input     |
| (CLI question)   |
+--------+---------+
         |
         v
+------------------------+
| Validate with Pydantic |
+--------+---------------+
         |
         v
+--------------------------+
|  Gemini 1.5 Flash Model  |
| (Generate AI Response)   |
+--------+-----------------+
         |
         v
+---------------------+
| Format & Validate   |
| AI Output (Pydantic)|
+--------+------------+
         |
         v
+------------------+
|  Print Response  |
|     in CLI       |
+------------------+
