# Level 2: Conversational Agent with Memory using Pydantic AI & Gemini

## 📌 Overview
This Level 2 agent builds Conversational Memory and The agent uses Google's Gemini 1.5 Flash model along with `pydantic-ai` for structured data handling, and logs activities using `logfire`.


## 🧠 Key Features

- 🧾 **Conversational Memory**: Tracks past user-AI exchanges to generate context-aware replies.
- 📄 **JSON Conversation History**: Saves the entire dialogue to a structured `conversation.json` file.
- ✅ **Input Validation**: Ensures valid user inputs using `pydantic`.
- 📊 **Logging and Tracing**: Tracks function-level execution and exceptions using `logfire`.
- 💬 **Concise Responses**: Configured to return short, accurate answers using Google's Gemini 1.5 Flash.

## Requirements
- `pydantic`
- `pydantic-ai`
- `google-generativeai`
- `logfire`
- `python-dotenv`


## ⚙️ How It Works

User inputs a question via the CLI interface.
Input is validated using Pydantic to ensure it's a proper query.
Recent conversation history (last 4 turns) is formatted into the prompt.
Gemini 1.5 Flash model processes the prompt and generates a response.
AI response is returned and displayed in the CLI.
Conversation history is updated, appending both the user question and AI response.
All exchanges are saved in conversation.json for persistent memory.
Logging and tracing are handled by logfire for transparency and debugging.

## 🧪 Sample Interaction
Your question: My name is Tripty and I am interested in compiler design and ML. What are some good career options?
Response: You can explore careers in AI research, data science, or systems software related to compilers.

Your question: What are some relevant textbooks that align with my interests?
Response: For ML, try "Deep Learning" by Goodfellow. For compilers, use the Dragon Book.
