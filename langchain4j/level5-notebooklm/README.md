# 1. Clean and build
mvn clean install

# 2. Set Keys 
# (Linux/macOS)
export OPENAI_API_KEY=your-key-here
export SEARCHAPI_KEY=your-key-here 
export HOST=host-address-weaviate
export WAPI_KEY=weaviate-api-key

# OR       # (Windows CMD)
set OPENAI_API_KEY=your-key-here
set SEARCHAPI_KEY=your-key-here  
set HOST=host-address-weaviate
set WAPI_KEY=weaviate-api-key

# OR       # (Windows Powershell)
$env:OPENAI_API_KEY = "your-key-here"
$env:SEARCHAPI_KEY = "your-key-here" 
$env:HOST = "host-address-weaviate"
$env:WAPI_KEY = "weaviate-api-key"


# 3. Run the app
mvn exec:java 
```bash
  mvn exec:java 
```
### Challenges Faced

- **Single-Agent Bottlenecks**
  → Linear RAG chains couldn't handle complex logic. Broken down into specialized agents to divide and conquer retrieval vs. reasoning.

- **Orchestration Complexity**
  → Managing hand-offs between agents was chaotic. Implemented a centralized Coordinator to parse intent before routing.

- **Tool vs. Context Confusion**
  → The model struggled to decide when to search the web vs. read the PDF. The Tool Agent now isolates external actions cleanly from internal retrieval.

- **Vector Store Instability**
  → Cloud vector DBs were too heavy for the local dev environment (RAM constraints). Abstracted the storage layer to allow hot-swapping between In-Memory and Weaviate/Chroma.

- **OCR Integration**
  → Scanned PDFs still cause noise. Encapsulated the ingestion logic to allow fallback strategies without breaking the main agent loop.

---

## Sample Flow (Conceptual)

=== Agent System Initialized. Awaiting Input. ===

- **You:** "What projects did I work on, and who founded the company mentioned in them?"

- **Coordinator:** *Analyzing intent...*
  1. Needs document data for "projects".
  2. Needs external info or deep reasoning for "founders".
  → *Dispatching to Retrieval Agent.*

- **Retrieval Agent:** *Scanning vector store...*
  → Found context: "WorqHat", "Symbolic Regression".
  → Returning context to QA Agent.

- **QA Agent:** *Analyzing context...*
  → Identified company "WorqHat". Missing founder info in docs.
  → Requesting Tool Agent intervention.

- **Tool Agent:** *Executing SearchAPI...*
  → Query: "Who founded WorqHat?"
  → Result: "Sagnik Ghosh and Susmita Ghosh."

- **AI (Final Synthesis):** Based on your documents, you worked on **Symbolic Regression** and **WorqHat**. External search confirms WorqHat was co-founded by **Sagnik Ghosh** and **Susmita Ghosh**.