# Podcast Generator Agent

This Python agent automates the creation of a two-person audio podcast from a YouTube video transcript or web page content. It extracts content, generates a concise summary, converts the summary into audio with alternating female and male voices, and provides an interactive CLI for answering questions about the content. The agent leverages Pydantic AI for agent-based task orchestration, ChromaDB for content storage, ElevenLabs for text-to-speech, and Logfire for logging.

## Features
- **Content Extraction**: Extracts text from YouTube video transcripts (if captions are enabled) or web pages.
- **Script Generation**: Creates a 100-150 word summary of the extracted content, focusing on key topics and takeaways.
- **Audio Generation**: Produces a two-person audio podcast with alternating female (Sarah) and male (Adam) voices per sentence.
- **Interactive Q&A**: Allows users to ask questions about the content via a CLI, with answers based on the extracted text.
- **Persistent Storage**: Uses ChromaDB to cache content, scripts, and audio metadata to avoid redundant processing.
- **Error Handling**: Includes robust error handling for API quotas, missing dependencies, and invalid inputs.
- **Logging**: Integrates Logfire for detailed logging of all operations and errors.

## Architecture
The script uses a modular, agent-based architecture orchestrated by Pydantic AI. Below is a simplified flow diagram:

```
+-------------------+       +-------------------+       +-------------------+       +-------------------+
|                   |       |                   |       |                   |       |                   |
| Content Extraction| ----> | Script Generation | ----> | Audio Generation  | ----> | Interactive Q&A   |
|      Agent        |       |      Agent        |       |      Agent        |       |      Agent        |
|                   |       |                   |       |                   |       |                   |
+-------------------+       +-------------------+       +-------------------+       +-------------------+
         |                          |                          |                          |
         v                          v                          v                          v
+-------------------+       +-------------------+       +-------------------+       +-------------------+
|                   |       |                   |       |                   |       |                   |
|  ChromaDB (Store  |       |  ChromaDB (Store  |       |  ChromaDB (Store  |       |  ChromaDB (Query  |
|   Extracted Text) |       |     Script)       |       |  Audio Metadata)  |       |   Content)        |
|                   |       |                   |       |                   |       |                   |
+-------------------+       +-------------------+       +-------------------+       +-------------------+
```

### Workflow
1. **Input**: User provides a YouTube video URL or web page URL via command-line argument.
2. **Content Extraction**: The Content Extraction Agent fetches the transcript (YouTube) or text (web page) and stores it in ChromaDB and a local file (`content_<uuid>.txt`).
3. **Script Generation**: The Script Generation Agent creates a 100-150 word summary, stores it in ChromaDB, and saves it to `script_<uuid>.txt`.
4. **Audio Generation**: The Audio Generation Agent converts the summary into a podcast with alternating female (Sarah, `EXAVITQu4vr4xnSDxMaL`) and male (Adam, `ErXwobaYiN019PkySvjV`) voices, saves it to `podcast_<uuid>.mp3`, and stores metadata in ChromaDB.
5. **Interactive Q&A**: The Query Agent allows users to ask questions about the content, retrieving answers from ChromaDB-stored text via an interactive CLI.

## Agents and Their Roles
The script uses four Pydantic AI agents, each responsible for a specific task:

1. **Content Extraction Agent**:
   - **Tool**: `extract_content`
   - **Function**: Extracts text from YouTube video transcripts (using `youtube-transcript-api`) or web pages (using `requests` and `BeautifulSoup`).
   - **Pydantic AI Role**: Orchestrates the extraction process, validates inputs via the `ContentInput` model, and ensures the content is saved to a file and ChromaDB.
   - **Output**: `content_<uuid>.txt` and ChromaDB entry.

2. **Script Generation Agent**:
   - **Tool**: `generate_script`
   - **Function**: Reads extracted content and generates a 100-150 word summary using the Gemini AI model.
   - **Pydantic AI Role**: Manages summarization, validates inputs via the `ScriptInput` model, and handles storage in ChromaDB and a local file.
   - **Output**: `script_<uuid>.txt` and ChromaDB entry.

3. **Audio Generation Agent**:
   - **Tool**: `generate_audio`
   - **Function**: Converts the summary into a two-person audio podcast using ElevenLabs, alternating female (Sarah) and male (Adam) voices per sentence.
   - **Pydantic AI Role**: Coordinates text-to-speech conversion, validates inputs via the `AudioInput` model, and manages audio file creation and ChromaDB metadata storage.
   - **Output**: `podcast_<uuid>.mp3` and ChromaDB metadata entry.

4. **Query Agent**:
   - **Tool**: `query_content`
   - **Function**: Retrieves content from ChromaDB and answers user questions via the Gemini AI model in an interactive CLI.
   - **Pydantic AI Role**: Facilitates content querying, validates inputs via the `QueryInput` model, and provides accurate responses based on stored content.
   - **Output**: CLI responses to user questions.

## Pydantic AI's Role
Pydantic AI (`pydantic-ai==0.2.17`) is central to the script's operation, providing:
- **Agent Orchestration**: Manages the execution of tasks by defining agents with specific tools and system prompts.
- **Input Validation**: Uses Pydantic models (`ContentInput`, `ScriptInput`, `AudioInput`, `QueryInput`) to validate inputs, ensuring type safety and correct data formats.
- **Tool Integration**: Enables seamless integration of custom tools (`extract_content`, `generate_script`, `generate_audio`, `query_content`) with the Gemini AI model.
- **Asynchronous Execution**: Supports async operations for efficient handling of API calls and file I/O.
- **Error Handling**: Simplifies error management by structuring agent responses and tool outputs.

## Prerequisites
- **Python**: 3.8 or higher
- **FFmpeg**: Installed and accessible via system PATH or `FFMPEG_PATH` in `.env`.
- **API Keys**:
  - Gemini AI (for content processing and Q&A)
  - ElevenLabs (for text-to-speech)
  - Logfire (for logging)
- **Dependencies**:
  ```bash
  pip install pydantic-ai==0.2.17 requests beautifulsoup4 python-dotenv elevenlabs==2.3.0 pydub youtube-transcript-api logfire chromadb
  ```

### Expected Output
Below is an example of terminal output (screenshot description):

```
--- Podcast Generation Result ---
Audio podcast generated successfully and saved to podcast_123e4567-e89b-12d3-a456-426614174000.mp3

--- Interactive Q&A ---
Content extracted from https://www.youtube.com/watch?v=8KkKuTCFvzI. Ask questions about the content or type 'exit' to quit.
Question: What is the main topic of the video?
Answer: The video discusses...
Question: exit
Exiting Q&A session.
```

## Acknowledgments
- **Pydantic AI**: For agent-based task orchestration and input validation.
- **ElevenLabs**: For high-quality text-to-speech voices.
- **Logfire**: For robust logging.
- **ChromaDB**: For persistent content storage.

