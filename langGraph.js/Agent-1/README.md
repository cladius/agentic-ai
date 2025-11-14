# 🧠 AI Assistant with LangGraph + Groq

This is a simple conversational AI assistant built using [LangGraph](https://github.com/langchain-ai/langgraphjs), [LangChain.js](https://js.langchain.com/), and the [Groq](https://groq.com/) language model API (`llama-3.3-70b-versatile`). It takes user input via the terminal and responds with concise, accurate replies using LLM inference.

---

## ✨ Features


- 🧠  **High-Quality AI Responses**:  
  Leverages the powerful `llama-3.3-70b-versatile` model from Groq for fast and accurate language generation.

- 🧩 **Graph-Based Flow with LangGraph**:  
  Implements a **graph-based flow** using `@langchain/langgraph` to model the conversation in a structured, node-based approach. The graph dynamically connects the start node, the chat node, and the end node.


- 🔁 **Single-turn conversational agent**  
  Accepts one user input at a time and responds using a compiled graph structure, ideal for quick queries or task-based interactions.

- 💬 **Terminal-based interaction**  
  Uses `prompt-sync` for synchronous user input directly in the command line interface (CLI), providing a conversational interface to interact with the AI.

- 📄 **Memory-Free Interaction**:  
  This version does not include memory, but it's easy to add memory (e.g., `BufferMemory` from LangChain) for multi-turn conversations, saving and recalling past inputs and responses.

- 🛠️ **Customizable Model Parameters**:  
  The model’s temperature and other parameters can be adjusted, allowing control over the randomness of responses and the model's behavior.

- 🚀 **Ready for extension**  
  Easily upgradeable to support memory, tools, multi-step graphs, or even branching logic.

---

## 🛠️ Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/Mishty-G01/Agentic_AI-LangGraph.js.git
cd Agentic_AI-LangGraph.js
cd Agent-1
```

### 2. Install dependencies
```bash
npm install
```

### 3. Create a .env file
Create a .env file in the root directory with your Groq API key:

```ini
GROQ_API_KEY="your_groq_api_key_here"
```
You can get a free API key from [Groq](https://console.groq.com).

### 🚀 Run the Assistant
```bash
node index.js
```
(Make sure you're using Node.js version 18 or above)

## 🧩 Project Structure

```bash
.
├── assets            # output images
├── node_modules      # Installed npm dependencies
├── .env              # Environment variables (contains GROQ_API_KEY)
├── index.js          # Main script containing the AI assistant logic
├── package-lock.json      # Project metadata and dependencies 
├── package.json       # Exact versions of installed packages
└── README.md          # Project documentation
```

## 🖼️ Example Result

Here is a sample output from the terminal after interacting with the assistant:

![AI Result Screenshot](./assets/result1.png)

![AI Result Screenshot](./assets/result2.png)
