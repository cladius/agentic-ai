# Conversational AI Agent

This project is a simple conversational AI assistant built using:

- [LangGraph](https://github.com/langchain-ai/langgraphjs) for managing conversational flow using graphs

- [LangChain](https://js.langchain.com/) for LLM integration and memory abstraction

- [Groq](https://console.groq.com/) for ultra-fast inference with LLaMA 3 models

- [BufferMemory](https://v03.api.js.langchain.com/classes/langchain.memory.BufferMemory.html)– to persist conversation history across user turns

It’s a step up from Agent 1, introducing Conversational Memory, which lets the agent remember previous questions and answers to provide context-aware responses. With BufferMemory for maintaining dialogue history, this project is an excellent starting point for anyone exploring how to build responsive, memory-enabled AI chat systems.
## Setup Instructions

### 1. Install dependencies

```bash
npm install
```

### 2. Create ```.env``` file
Create a ```.env``` file in the root directory with your Groq API key:

```ini
GROQ_API_KEY=your-groq-api-key-here
```
You can get your API key from: https://console.groq.com

### 3. Running the Assistant

```bash
node index.js
```
Then chat with the assistant.  Type exit to quit the conversation.

## Graph Structure

Here is the visual representation of the LangGraph workflow.

![Graph Structure](./assets/graph.png)

## How Memory Works (Step-by-Step)

We use ```BufferMemory``` to keep track of the entire conversation so the AI assistant can generate context-aware responses. Here’s how it works:

Create a ```BufferMemory``` instance
- Load memory → get history
- Build new message list: ```SystemMessage``` + history + ```HumanMessage```
- Call the LLM
- Save the interaction (input, output) into memory
    
    This is repeated for every message you send


## Usage

Once started, you can chat with the assistant in your terminal:

```
User: My name is Sakhi, and I am an engineering student interested in compiler design and ML. What are some good career options?
AI: (some answer from LLM)
User: What are some relevant textbooks that align with my interests?
AI: (based on prior info.... )
```

To exit:
```
You: exit
```

## Example Result

Here is a sample output from the terminal after interacting with the assistant:

![AI Result Screenshot](./assets/result1.png)

![AI Result Screenshot](./assets/result2.png)

The agent remembers the previous state/chat while responding to current query. 