Document Q&A WorkFlow
--
l4-w.py is an advanced example script that demonstrates how to build an end-to-end document question answering (Q&A) workflow using the Agno framework, the Gemini language model, and ChromaDB for vector storage.

What does this file do?

1. Loads environment variables and API keys from a .env file for secure configuration.
2. Downloads and chunks a PDF from a specified URL.
3. Embeds the PDF content using Gemini embeddings and stores it in a Chroma vector database for semantic search.
4. Defines a workflow class that:

    i. Accepts user questions.
   
    ii. Searches the vector database for relevant information.
   
    iii. Uses a Gemini-powered agent to answer questions based on the PDF content.

    iv. Caches answers for repeated questions to improve efficiency.

    v. Handles Google API quota errors with exponential backoff and retry logic.

5. Persists workflow state using SQLite storage for durability.
6. Launches an interactive Agno Playground web UI for users to ask questions about the PDF and receive answers in real time.

How to use

1. Install dependencies - *pip install agno chromadb google-genai python-dotenv*
2. Set up your environment
    Create a .env file in the project directory and add your API keys:
     *GOOGLE_API_KEY=your_google_api_key*
   
     *AGNO_API_KEY=your_agno_api_key*

3. Run the script: *python l4-w.py*
4. Open the web interface: 
Follow the instructions in the terminal to access the Agno Playground and interact with the document Q&A workflow.

Customization:

- Change the PDF URL in the script to use your own document.
- Adjust the workflow or agent instructions to fit your use case.

Dependencies:

- agno
- chromadb
- google-genai
- dotenv
- sqlite3

This script is ideal for building interactive, document-aware AI assistants that can answer questions based on the content of uploaded or linked PDFs.

OUTPUT:
--
Link for the PDF used here: https://www.adobe.com/support/products/enterprise/knowledgecenter/media/c4611_sample_explain.pdf

![image](https://github.com/user-attachments/assets/f2e8fb04-2517-42cc-8755-76932f6ebe2f)

