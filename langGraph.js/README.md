# LangGraph.js

Welcome to the LangGraph.js repository! This is a collection of 5 distinct AI agents, each built using [Node.js](https://nodejs.org/), [LangChain.js](https://js.langchain.com/docs/introduction/), and the [LangGraph.js](https://langchain-ai.github.io/langgraphjs/) library.

> Want to understand the problem each agent solves?
> [View the Official Problem Statement](https://github.com/cladius/agentic-ai/blob/master/sample_problem.md)

## What is LangGraph.js?
[LangGraph.js](https://langchain-ai.github.io/langgraphjs/) is a JavaScript library for building **robust** and **stateful** applications with Large Language Models (LLMs). It lets you design workflows as **graphs**, where each **node** performs a task—like an agent action or tool call—updating a shared **state** (containing inputs, intermediate results, or conversation history), and **edges** control the flow between nodes, including conditional paths.

## Key Features
- **Graph-based Workflow**: Model complex agent behaviors using directed graphs(nodes+edges).

- **Stateful Execution**: Maintains a shared, updatable state across all nodes (steps), enabling agents to retain context and memory.

- **Multi-Agent Coordination**: Facilitates the creation of workflows where different agents can call upon each other or specialized tools.

- **Flexible Logic**: Supports loops and conditional paths, allowing agents to repeat steps or adapt based on results.

- **Extensible**: Easily add new nodes, tools, or agents to expand functionality.

- **Human-in-the-Loop**: Supports integration of human oversight and intervention, allowing for inspection and modification of agent state during execution.

## Prerequisites
- [Node.js (v18+)](https://nodejs.org/) - runtime environment
- [GROQ_API_KEY](https://console.groq.com/keys) - for Groq LLMs
- (Optional) [TAVILY_API_KEY](https://app.tavily.com/home) - real-time search (Agent-3)
- (Optional) [Docker Desktop](https://www.docker.com/products/docker-desktop)  - required for ChromaDB vector store (Agents 4 & 5)
- (Optional) Google Cloud service account JSON - for podcast [Text-to-Speech API](https://cloud.google.com/text-to-speech?hl=en) (Agent-5)

---

### **Documentation**
Check out the [LangGraph_documentation](https://github.com/user-attachments/files/23729518/LangGraph_Report.pdf)

