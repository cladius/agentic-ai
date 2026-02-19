# LangChain4j Agents Exploration  
## LangChain4j Internship Projects Repository

This repository contains a set of **hands-on projects** built using **LangChain4j (Java)**.

The projects move from a basic LLM-backed Java interface to more advanced setups involving memory, tools, document retrieval, and multi-agent coordination. The focus is on understanding how agent systems are built in practice, step by step.

---

## What is LangChain4j?

LangChain4j is a **Java framework for building LLM-powered applications**. It provides abstractions for working with language models, memory, tools, and structured workflows in a Java-friendly way.

### Core capabilities:
- **Annotated Interfaces**: Define AI behavior using Java annotations.
- **LLM Integration**: Work with OpenAI-compatible chat models.
- **Chat Memory**: Maintain context across multiple user interactions.
- **Tool Calling**: Allow agents to invoke external tools such as web search or APIs.
- **Embeddings & Vector Stores**: Store and retrieve knowledge using similarity search.
- **RAG Support**: Build document-based question answering systems.
- **Multi-Agent Patterns**: Separate retrieval, reasoning, and tool execution logic.

---

## What This Repository Covers

Across the different modules, the repository demonstrates:

- Stateless LLM interactions using annotated Java interfaces  
- Context-aware conversations using local memory  
- Agents that can call external tools (e.g., web search)  
- Document ingestion with OCR, embeddings, and vector retrieval  
- Retrieval-Augmented Generation (RAG) for document Q&A  
- Multi-agent setups with explicit routing and coordination  
- Delegation to external services (e.g., MCP-based tools)

Each concept is introduced incrementally to keep the learning curve manageable.

---

## Repository Structure

Each folder is self-contained and includes:
- A description of what the module does
- The main architectural ideas used
- Instructions to build and run the code
- Notes on issues or limitations encountered

---

## APIs, Tools, and Dependencies

Depending on the module, you may need:
- An OpenAI-compatible LLM API (Demo API support is provided by Langchain4j)
- SearchAPI for web search
- OCR tools (Apache Tika, Tesseract)
- Vector stores (In-Memory, Weaviate, Chroma)
- Node.js (for MCP-based external tools)
- Maven for building and running Java projects

Configuration is handled using environment variables or a `.env` file.

---

## Notes for Beginners

- Most complexity comes from **orchestration**, not the LLM itself.
- Tool usage must be explicitly guided through prompts or system messages.
- RAG systems require careful handling of document size, chunking, and embeddings.
- Multi-agent designs simplify reasoning but add coordination overhead.
- Debugging often happens at runtime due to dynamic agent bindings.
- Official Documentation: https://docs.langchain4j.dev/ 
- More examples: https://github.com/langchain4j/langchain4j-examples 
---

## Purpose of This Repository

This repository is meant as a **learning and experimentation space**, It reflects real development challenges encountered while working with LangChain4j and agent-based architectures in Java. 
