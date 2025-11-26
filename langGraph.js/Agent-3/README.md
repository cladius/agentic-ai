# AI Assistant with Real-Time Web Search

This project is a **web-enabled AI conversational assistant** built with [LangGraph](https://langchain-ai.github.io/langgraphjs/), [Groq](https://groq.com), and [Tavily](https://tavily.com). It supports **real-time web search** via Tavily, **conversation history** with LangChain’s `ChatMessageHistory`, and **summarization** of search results.

Perfect for beginners, this assistant demonstrates how AI can integrate real-time data and memory to answer user queries intelligently.

## About Tavily
**Tavily** is a web search tool that indexes and retrieves up-to-date information from the internet. It works by scanning multiple sources in real time, ranking results for relevance, and returning structured content that can be easily processed by applications or AI systems. Tavily essentially acts as a bridge between live web data and AI models, providing fast access to current facts, news, and other web content.

## Features
- Uses the **Tavily Search Tool** for queries requiring **current or real-time information**
- Handles general knowledge, greetings, and follow-ups naturally
- **LLM reasoning** powered by Groq’s `meta-llama/llama-4-maverick-17b-128e-instruct`
- **Session memory** with `ChatMessageHistory` for context-aware responses
- **Summarization** of search results for concise output
- Supports **continuous interaction**, allowing multi-turn conversation until the user exits
- Input validation with **Zod** – ensures user queries are correctly formatted and reliable before processing

## Graph Structure

Here is the visual representation of the LangGraph workflow.

![Graph Structure](./assets/graph.png)

## Getting Started

### 1. Install dependencies

```bash
npm install
```

### 2. Set up environment variables
Create ```.env``` file in root directory:
Add your API keys inside it.

```bash
GROQ_API_KEY=your_groq_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

Groq: Get your API key from [Groq Console](https://console.groq.com/home).\
Tavily: Get your API key from [Tavily Dashboard](https://app.tavily.com/home).

### 3. Running the Assistant

```bash
node index.js
```
Then chat with your assistant.  Type exit to quit the conversation.

## Usage

Once started, you can chat with the assistant in your terminal:

```
Hi user! I am your AI Assistant. Let's chat.
You: What is the capital of Japan?
Agent: The capital of Japan is Tokyo. 

You: What’s the latest news about AI chips?
Agent: [Summarized real-time info...]
```

To exit:
```
You: exit
```

## Example Result

Here is a sample output from the terminal after interacting with the assistant:

![AI Result Screenshot](./assets/image.png)

## **Demo**
Check out a demo video of the project [here](https://github.com/user-attachments/assets/caf41d65-56b2-4cf3-a3fd-9246a84ac1f5)