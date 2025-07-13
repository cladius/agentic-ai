# Level 4 Pdf agent (`pdf.py`)

## Overview
The `Pdf.py` agemt is a Python application designed to extract text from PDF files, store it in a ChromaDB vector store, and answer user questions about the content. It leverages the Gemini AI model for question-answering and uses `PyPDF2` for text extraction. The agent processes PDFs like `solarsystem.pdf`, chunking text for efficient storage and retrieval in ChromaDB using `sentence-transformers` embeddings. It supports interactive Q&A, saves metadata in `pdf_metadata.json`, and integrates Logfire for detailed logging, making it ideal for analyzing document content.

## Features
- Extracts text from text-based PDFs and chunks it into ~500-character segments.
- Stores text chunks with embeddings in ChromaDB for efficient retrieval.
- Supports interactive Q&A with concise answers (1-2 sentences) based on PDF content.
- Validates PDF files for readability and format.
- Saves metadata (PDF path, ChromaDB collection, timestamp) to `pdf_metadata.json`.
- Logs all steps (validation, extraction, storage, queries) via Logfire.


## Requirements
- **Python**: 3.8+
- **Dependencies**:
  ```bash
  pip install pydantic-ai==0.2.17 python-dotenv logfire PyPDF2 chromadb sentence-transformers
  ```
- **Environment Variables** (in `.env`):
  ```plaintext
  GEMINI_API_KEY=your_gemini_key
  LOGFIRE_TOKEN=your_logfire_token
  ```
- **Hardware**: Standard PC with internet access.
- **PDF Files**: Text-based PDFs (e.g., `.pdf` files with extractable text, not scanned images).

## How It Works (Workflow)
1. **Input**: User provides a PDF file path (e.g., `solarsystem.pdf`) via command line.
2. **Validation**: The script checks if the PDF exists, is in `.pdf` format, and is readable using `PyPDF2`.
3. **Text Extraction**:
   - Extracts text from each page and splits it into ~500-character chunks.
   - Logs extraction details via Logfire.
4. **ChromaDB Storage**:
   - Generates embeddings for chunks using `sentence-transformers` (`all-MiniLM-L6-v2`).
   - Stores chunks in a unique ChromaDB collection (e.g., `pdf_solarsystem_abcdef12`).
5. **Metadata Storage**: Saves PDF path, collection name, and timestamp to `pdf_metadata.json`.
6. **Interactive Q&A**:
   - User asks questions (e.g., “Summary of the content?”).
   - The Query Agent retrieves relevant chunks from ChromaDB and generates concise answers.
7. **Output**: Displays extraction status and Q&A responses in the terminal.

## Agents and Their Work
- **Extraction Agent**:
  - **Model**: `google-gla:gemini-1.5-pro`
  - **Role**: Uses the `extract_pdf` tool to process PDFs.
  - **Task**: Validates the PDF, extracts text, chunks it, stores it in ChromaDB, and saves metadata.
- **Query Agent**:
  - **Model**: `google-gla:gemini-1.5-pro`
  - **Role**: Uses the `query_pdf_content` tool to answer questions.
  - **Task**: Retrieves top-3 relevant chunks from ChromaDB based on question embeddings and generates concise (1-2 sentence) answers.

## Pydantic AI Role
- **Input Validation**: Uses Pydantic models (`PdfExtractionInput`, `QueryInput`) to validate PDF paths and user questions.
- **Tool Framework**: Defines `extract_pdf` and `query_pdf_content` tools for agent interactions.
- **Structured Data**: Ensures consistent handling of metadata and query responses.
- **Error Handling**: Facilitates robust error reporting for invalid PDFs, extraction failures, or query issues.

## Flow Diagram
```mermaid
graph TD
    A[User Input: PDF Path] --> B{Validate PDF}
    B -->|Valid| C[Extract Text]
    B -->|Invalid| D[Error Message]
    C --> E[Chunk Text]
    E --> F[Extraction Agent]
    F --> G[Generate Embeddings]
    G --> H[Store in ChromaDB]
    H --> I[Save Metadata]
    I --> J[Display Extraction Status]
    J --> K[Interactive Q&A]
    K --> L[Query Agent]
    L --> M[Retrieve Chunks]
    M --> N[Generate Answer]
    N --> O[Display Answer]
    K -->|Exit| P[End]
```

## Expected Output
For a PDF like `solarsystem.pdf` containing information about the solar system:
```
Starting PDF Q&A script
Logfire project URL: https://logfire-eu.pydantic.dev/triptytiwari07/pydantic
Validated PDF: C:\Users\tript\OneDrive\Desktop\py\Level5\solarsystem.pdf
Attempting to extract PDF: C:\Users\tript\OneDrive\Desktop\py\Level5\solarsystem.pdf

Attempting to extract PDF: C:\Users\tript\OneDrive\Desktop\py\Level5\solarsystem.pdf

Extracting content from: C:\Users\tript\OneDrive\Desktop\py\Level5\solarsystem.pdf
Validated PDF: C:\Users\tript\OneDrive\Desktop\py\Level5\solarsystem.pdf
Extracted 20 chunks from C:\Users\tript\OneDrive\Desktop\py\Level5\solarsystem.pdf
Stored 20 chunks in ChromaDB collection: pdf_solarsystem_abcdef12
Saved metadata for C:\Users\tript\OneDrive\Desktop\py\Level5\solarsystem.pdf to pdf_metadata.json
Extraction result: Successfully extracted and stored content from C:\Users\tript\OneDrive\Desktop\py\Level5\solarsystem.pdf

--- PDF Extraction ---
Successfully extracted and stored content from C:\Users\tript\OneDrive\Desktop\py\Level5\solarsystem.pdf

--- Interactive Q&A ---
PDF processed: C:\Users\tript\OneDrive\Desktop\py\Level5\solarsystem.pdf. Ask questions or type 'exit' to quit.
Question: Summary of the content?
User asked: Summary of the content?
Answering question 'Summary of the content?' for PDF: C:\Users\tript\OneDrive\Desktop\py\Level5\solarsystem.pdf
Found metadata for PDF: C:\Users\tript\OneDrive\Desktop\py\Level5\solarsystem.pdf
Retrieved 3 chunks for question
Query response: The document describes the solar system, including eight planets orbiting the Sun, their characteristics, and notable features like Jupiter’s gas composition and Mercury’s proximity to the Sun.

Answer: The document describes the solar system, including eight planets orbiting the Sun, their characteristics, and notable features like Jupiter’s gas composition and Mercury’s proximity to the Sun.

Question: What is the largest planet?
Answer: Jupiter is the largest planet in the solar system, known for its massive gas composition.

Question: exit

Exiting Q&A session.
```
