# Web Content Analysis Agent (`web.py`)

## Overview
The `web.py` agent analyzes web page content by extracting text, summarizing it, and answering user questions. It uses a text-based AI model to process URLs provided by the user, generating concise summaries and supporting interactive Q&A. Results are stored in a JSON file for persistence, with Logfire logging for debugging.

## Features
- Extracts and summarizes text from any web page URL.
- Supports interactive Q&A about web content.
- Validates URLs for accessibility and content.
- Saves summaries in chromadb
- Logs execution details via Logfire.

## Requirements
- **Python**: 3.8+
- **Dependencies**:
  ```bash
  pip install pydantic-ai==0.2.17 python-dotenv logfire requests beautifulsoup4
  ```
- **Environment Variables** (in `.env`):
  ```plaintext
  GEMINI_API_KEY=your_gemini_key
  LOGFIRE_TOKEN=your_logfire_token
  ```
- **Hardware**: Standard PC with internet access.

## How It Works (Workflow)
1. **Input**: User provides a URL via command line.
2. **Validation**: Checks URL accessibility and content presence using `requests` and `beautifulsoup4`.
3. **Content Extraction**:
   - Extracts text from the web page.
   - The Analysis Agent generates a summary (100-150 words).
4. **Storage**: Saves the summary to `web_content.json`.
5. **Q&A**:
   - The Query Agent answers user questions based on the summary.
   - Displays answers in the terminal.
6. **Logging**: Logs steps via Logfire.

## Agents and Their Work
- **Analysis Agent**:
  - **Model**: `google-gla:gemini-1.5-pro`
  - **Role**: Uses the `analyze_web_content` tool to extract and summarize text.
  - **Task**: Produces a 100-150 word summary of the web page.
- **Query Agent**:
  - **Model**: `google-gla:gemini-1.5-pro`
  - **Role**: Uses the `query_web_content` tool to answer questions.
  - **Task**: Provides concise answers based on the stored summary.

## Pydantic AI Role
- **Input Validation**: Uses Pydantic model (`WebAnalysisInput`) to validate URLs.
- **Tool Framework**: Defines `analyze_web_content` and `query_web_content` tools.
- **Structured Data**: Manages JSON storage of summaries.
- **Error Handling**: Handles invalid URLs or extraction failures.

## Flow Diagram
```mermaid
graph TD
    A[User Input: URL] --> B{Validate URL}
    B -->|Valid| C[Extract Content]
    B -->|Invalid| D[Error Message]
    C --> E[Analysis Agent]
    E --> F[Gemini Model]
    F --> G[Generate Summary]
    G --> H[Save to web_content.json]
    H --> I[Display Summary]
    I --> J[Interactive Q&A]
    J --> K[Query Agent]
    K --> L[Load Summary]
    L --> M[Answer Question]
    M --> N[Display Answer]
    J -->|Exit| O[End]
```

*Example Output*:
```
Analyzing: https://example.com
--- Summary ---
The page introduces Example.com, a placeholder domain...
--- Q&A ---
Question: What is the website about?
Answer: The website is a placeholder domain for testing.
```