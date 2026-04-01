# 📘 Level 4 — Document Q&A with LangChain4j

## LLM-powered Question Answering
### Document Ingestion, Embedding & Retrieval Augmented Generation (RAG)

---

## Features

- PDF / Image ingestion with optional OCR (Apache Tika + Tesseract)
- Embedding generation using OpenAI
- In-memory vector store for fast similarity search
- Agent-style conversational interface for document Q&A
- Web search fallback using SearchAPI tool

---

## Run Steps

```bash
# 1. Clean and build
mvn clean install

# 2. Set Keys 
# (Linux/macOS)
export SEARCHAPI_KEY=your-key-here 
export HOST = host-address-weaviate
export WAPI_KEY = weaviate-api-key
# OR      # (Windows CMD)
set SEARCHAPI_KEY=your-key-here  
set HOST= host-address-weaviate
set WAPI_KEY= weaviate-api-key
# OR       # (Windows Powershell)
$env:SEARCHAPI_KEY = your-key-here 
$env:HOST = host-address-weaviate
$env:WAPI_KEY = weaviate-api-key

```

# 3. Run the app
mvn exec:java 
```bash
  mvn exec:java 
```
### Challenges Faced

- Complex & inconsistent syntax across LangChain4j APIs
  →  Several methods like .builder() or .entries() were missing or undocumented, requiring trial-and-error and reading source code.

- **OCR integration issues with Tika and tess4j**
  →OCR failed silently or conflicted with text-based parsers on hybrid (scanned + digital) PDFs. Required tuning Tika configs and error handling.

- **Embedding overflow** due to large document input  
  → Implemented chunking logic before embedding.

- **Cloud vector stores (e.g., ChromaDB, Weaviate) required Docker setups**
  → Local vector DBs were too heavy to run on limited RAM, making cloud-based or persistent storage infeasible during development.

- **OCR + Tika conflicts** when both text and image data present  
  → Configured fallback strategy for hybrid parsing.
- **Docker dependency for running local vector stores**
- → System constraints (insufficient RAM) prevented running Docker containers, so the project was limited to InMemoryEmbeddingStore for now

---

## Sample Chat


=== Ask questions about the documents (type 'exit' to quit) ===

- You: What is my github username
- AI: Your GitHub username is rzx01.

- You: What is my cgpa
- AI: Your CGPA is 8.42.

- You: Provide names of the repos ive worked on
- AI: The names of the repositories you have worked on include:

1. **Symbolic Regression using Hybrid Genetic Algorithm & Neural Network**
2. **Pywiz: Gamified Python Learning**
3. **Weblint: Web User Behavioral Analysis**
4. **Study Vault: Centralized College Resource**
5. **Personalized Recommendation Engine**

- These are based on the projects mentioned in the provided context.

- You: What year was i born?
- AI: Based on the provided education timeline, you completed your 10th standard in June 2020 and were likely around 16 years old at that time. This suggests that you were born around 2004.

- You: which company did i work for
- AI: You worked for WorqHat as a Fullstack Developer.

- You: search and tell me who founded the company
- AI: WorqHat was co-founded by Sagnik Ghosh and Susmita Ghosh. Sagnik Ghosh also serves as the CEO of the company.

