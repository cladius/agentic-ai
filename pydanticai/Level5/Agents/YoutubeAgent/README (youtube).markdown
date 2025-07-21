# YouTube Video Analysis Agent (`youtube.py`)

## Overview
The `youtube.py` agent analyzes YouTube video transcripts, generating summaries and answering user questions. It uses a text-based AI model to process video URLs, extracting transcripts via an  YouTube Data API and summarizing content. The agent supports interactive Q&A and stores results in a JSON file, with Logfire logging for debugging. 

## Features
- Extracts and summarizes YouTube video transcripts.
- Supports interactive Q&A about video content.
- Validates YouTube URLs and transcript availability.
- Saves summaries in Chroma db
- Logs execution via Logfire.


## Requirements
- **Python**: 3.8+
- **Dependencies**:
  ```bash
  pip install pydantic-ai==0.2.17 python-dotenv logfire google-api-python-client
  ```
- **Environment Variables** (in `.env`):
  ```plaintext
  GEMINI_API_KEY=your_gemini_key
  LOGFIRE_TOKEN=your_logfire_token
  ```
- **Hardware**: Standard PC with internet access.

## How It Works (Workflow)
1. **Input**: User provides a YouTube video URL via command line.
2. **Validation**: Checks URL validity and transcript availability using the YouTube API.
3. **Transcript Extraction**:
   - Retrieves the video transcript.
   - The Analysis Agent generates a summary (100-150 words).
4. **Storage**: Saves the summary to `youtube_content.json`.
5. **Q&A**:
   - The Query Agent answers user questions based on the summary.
   - Displays answers in the terminal.
6. **Logging**: Logs steps via Logfire.

## Agents and Their Work
- **Analysis Agent**:
  - **Model**: `google-gla:gemini-1.5-pro`
  - **Role**: Uses the `analyze_youtube_content` tool to summarize transcripts.
  - **Task**: Produces a 100-150 word summary of the video.
- **Query Agent**:
  - **Model**: `google-gla:gemini-1.5-pro`
  - **Role**: Uses the `query_youtube_content` tool to answer questions.
  - **Task**: Provides concise answers based on the stored summary.

## Pydantic AI Role
- **Input Validation**: Uses Pydantic model (`YouTubeAnalysisInput`) to validate URLs.
- **Tool Framework**: Defines `analyze_youtube_content` and `query_youtube_content` tools.
- **Structured Data**: Manages JSON storage of summaries.
- **Error Handling**: Handles invalid URLs or transcript issues.

## Flow Diagram
```mermaid
graph TD
    A[User Input: YouTube URL] --> B{Validate URL}
    B -->|Valid| C[Extract Transcript]
    B -->|Invalid| D[Error Message]
    C --> E[Analysis Agent]
    E --> F[Gemini Model]
    F --> G[Generate Summary]
    G --> H[Save to youtube_content.json]
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
Analyzing: https://youtube.com/watch?v=example
--- Summary ---
The video explains machine learning basics...
--- Q&A ---
Question: What is the video about?
Answer: The video covers machine learning fundamentals.
```