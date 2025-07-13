# Image Analysis Agent (`image.py`)

## Overview
The `image.py` agent is a Python application that leverages AI vision capabilities to analyze any image and generate detailed descriptions. It uses the Gemini Vision model  to produce 100-150 word descriptions of image. The agent supports interactive Q&A, allowing users to ask questions about the image based on the generated description. Logfire integration provides detailed monitoring for debugging.

## Features
- Analyzes any image with detailed descriptions (100-150 words).
- Supports interactive Q&A for image-related questions (e.g., “What is the subject’s color?”).
- Validates image quality (size >100x100 pixels, <2MB, sufficient contrast).
- Logs image properties and analysis steps via Logfire.
- Saves descriptions with timestamps for reuse.

## Requirements
- **Python**: 3.8+
- **Dependencies**:
  ```bash
  pip install pydantic-ai==0.2.17 python-dotenv logfire pillow numpy
  ```
- **Environment Variables** (in `.env`):
  ```plaintext
  GEMINI_API_KEY=your_gemini_key
  LOGFIRE_TOKEN=your_logfire_token
  ```
- **Hardware**: Standard PC with internet access.
- **Image Files**: Supported formats (`.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`).

## How It Works (Workflow)
1. **Input Validation**: User provides an image path (e.g., `cat.jpg`) via command line. The script validates the image’s existence, format, size, and contrast using Pillow and NumPy.
2. **Metadata Reset**: Deletes `image_metadata.json` to ensure fresh analysis.
3. **Image Analysis**:
   - The Analysis Agent uses Gemini Vision to generate a 100-150 word description, focusing on subjects, colors, background, and lighting.
   - Results are logged via Logfire and saved to `image_metadata.json`.
4. **Interactive Q&A**:
   - The Query Agent loads the description and answers user questions (e.g., “What is the background?”).
   - Validates description relevance for each question, prompting re-analysis if details are missing.
5. **Output**: Displays the description and Q&A responses in the terminal.

## Agents and Their Work
- **Analysis Agent**:
  - **Model**: `google-gla:gemini-1.5-pro`
  - **Role**: Analyzes the image using the `analyze_image` tool.
  - **Task**: Generates a detailed description (100-150 words) based on visible elements, avoiding assumptions.
- **Query Agent**:
  - **Model**: `google-gla:gemini-1.5-pro`
  - **Role**: Handles user questions using the `query_image_content` tool.
  - **Task**: Retrieves the stored description and provides concise, accurate answers, validating relevance.

## Pydantic AI Role
- **Input Validation**: Uses Pydantic models (`ImageAnalysisInput`, `QueryInput`) to validate image paths and user questions.
- **Tool Framework**: Defines `analyze_image` and `query_image_content` tools for agent interactions.
- **Structured Data**: Ensures consistent data handling for image metadata and agent outputs.
- **Error Handling**: Facilitates robust error reporting for invalid inputs or analysis failures.

## Flow Diagram
```mermaid
graph TD
    A[User Input: Image Path] --> B{Validate Image}
    B -->|Valid| C[Delete Metadata]
    B -->|Invalid| D[Error Message]
    C --> E[Analysis Agent]
    E --> F[Gemini Vision Model]
    F --> G[Generate Description]
    G --> H[Save to image_metadata.json]
    H --> I[Display Description]
    I --> J[Interactive Q&A]
    J --> K[Query Agent]
    K --> L[Load Description]
    L --> M{Validate Relevance}
    M -->|Relevant| N[Answer Question]
    M -->|Irrelevant| O[Prompt Re-analysis]
    N --> P[Display Answer]
    J -->|Exit| Q[End]
```

*Example Output*:
```
Attempting to analyze image: C:\Users\tript\OneDrive\Desktop\py\Level5\dog.jpg
--- Image Analysis ---
The image depicts a brown dog standing on a grassy park field...
--- Interactive Q&A ---
Question: What is the dog colour?
Answer: The dog’s fur is a rich chestnut brown.
```