

# 🤖 Vertex AI RAG Agent with Google ADK

This project demonstrates how to build an intelligent agent using **Google's Agent Development Kit (ADK)** and **Vertex AI RAG (Retrieval-Augmented Generation)** to retrieve and answer user queries from a custom document corpus.

---

## 🚀 Features

* 💬 Conversational Agent powered by `gemini-2.0-flash-001`
* 📄 Retrieves relevant information using Vertex AI RAG
* 🧠 Maintains session context across messages
* 🔧 Tool-based agent with modular retrieval logic
* 📝 Interactive CLI with rich logs and error handling

---

## 📦 Project Structure

```
.
├── .env                     # Environment variables
├── main.py                  # Main interactive agent loop
├── prompts.py               # Prompt/instruction templates
├── README.md                # This file 😄
```

---

## ⚙️ Setup Instructions

### 1️⃣ Prerequisites

* Python 3.8+
* Google Cloud project with Vertex AI enabled
* Vertex AI corpus created (for RAG)
* `GOOGLE_API_KEY` with access to Gemini
* `.env` file with required variables

### 2️⃣ Clone the Repo

```bash
git clone https://github.com/yourusername/vertex-ai-rag-agent.git
cd vertex-ai-rag-agent
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

<details>
<summary>🔍 Example <code>requirements.txt</code></summary>

```
python-dotenv
google-cloud-aiplatform
google-generativeai
google-adk
```

</details>

---

## 🔐 Environment Setup

Create a `.env` file in the root directory:

```env
GOOGLE_API_KEY=your_api_key_here
RAG_CORPUS=your_vertex_ai_rag_corpus_id
```

---

## 🧠 How It Works

1. Loads your API key and RAG corpus from `.env`.
2. Initializes a RAG retrieval tool using `VertexAiRagRetrieval`.
3. Defines an **ADK agent** with:

   * Gemini model (`gemini-2.0-flash-001`)
   * Retrieval tool
   * Custom instructions from `prompts.py`
4. Maintains session state using `InMemorySessionService`.
5. Accepts user input and streams the response asynchronously.

---

## 🧪 Run the Agent

```bash
python main.py
```

You’ll see:

```
Vertex AI RAG Agent is running. Type 'exit' to quit.
Ask a question to retrieve documentation from the RAG corpus!

--- Example conversation: ---
You could ask: 'What is the latest documentation on Vertex AI RAG?'
Then follow up with: 'Can you provide more details on RAG corpus setup?'
--- End example ---
```

---

## 🛠️ Troubleshooting

* ❌ **Missing .env values?**

  > Make sure `GOOGLE_API_KEY` and `RAG_CORPUS` are defined.

* 🔐 **SSL Error or API Timeout?**

  > Check your internet connection and API credentials.

* 🗂️ **Corpus not found?**

  > Verify that `RAG_CORPUS` exists in Vertex AI Search.

* 🔁 **Session not persisting?**

  > This version uses `InMemorySessionService`. For production, swap with a persistent backend.

---

## 📚 Resources

* [🔗 Google Agent Development Kit (ADK) Docs](https://cloud.google.com/agent-development/docs)
* [🔗 Vertex AI RAG Documentation](https://cloud.google.com/vertex-ai/docs/generative-ai/agent-rag-overview)
* [🔗 Gemini API](https://ai.google.dev/)

---
<img width="961" alt="Screenshot 2025-05-27 at 11 25 13 AM" src="https://github.com/user-attachments/assets/96d6a6f1-43e6-4f54-b5e7-08254a8a427e" />

