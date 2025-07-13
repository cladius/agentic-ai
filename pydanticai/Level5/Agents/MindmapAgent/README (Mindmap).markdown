# Mindmap Generation Agent (`mindmap.py`)

## Overview
The `mindmap.py` agent generates mindmaps from user-provided topics using a text-based AI model. It creates structured, hierarchical mindmaps in image format. The agent uses a generative AI model to produce detailed mindmap structures, with nodes and subnodes representing ideas and relationships. Results are saved to a JSON file for persistence, and Logfire logs execution details.

## Features
- Generates mindmaps for any user-specified topic.
- Produces hierarchical JSON output with nodes and subnodes.
- Validates user input for topic relevance.
- Saves mindmap data to `mindmap.json`.
- Logs execution via Logfire for debugging.

## Requirements
- **Python**: 3.8+
- **Dependencies**:
  ```bash
  pip install pydantic-ai==0.2.17 python-dotenv logfire
  ```
- **Environment Variables** (in `.env`):
  ```plaintext
  GEMINI_API_KEY=your_gemini_key
  LOGFIRE_TOKEN=your_logfire_token
  ```
- **Hardware**: Standard PC with internet access.

## How It Works (Workflow)
1. **Input**: User provides a topic (e.g., “Machine Learning”) via command line.
2. **Validation**: The script checks if the topic is valid (non-empty, relevant).
3. **Mindmap Generation**:
   - The Mindmap Agent generates a hierarchical structure using the AI model.
   - Nodes represent main ideas, with subnodes for details.
4. **Storage**: Saves the mindmap as JSON to `mindmap.json`.
5. **Output**: Displays the mindmap structure in the terminal and logs details via Logfire.

## Agents and Their Work
- **Mindmap Agent**:
  - **Model**: `google-gla:gemini-1.5-pro`
  - **Role**: Uses the `generate_mindmap` tool to create the mindmap.
  - **Task**: Produces a JSON structure with nodes and subnodes based on the topic, ensuring logical hierarchy.

## Pydantic AI Role
- **Input Validation**: Uses Pydantic model (`MindmapInput`) to validate the topic.
- **Tool Framework**: Defines the `generate_mindmap` tool for agent interaction.
- **Structured Output**: Ensures JSON output is well-formed for downstream use.
- **Error Handling**: Manages invalid topic inputs or generation failures.

## Flow Diagram
```mermaid
graph TD
    A[User Input: Topic] --> B{Validate Topic}
    B -->|Valid| C[Mindmap Agent]
    B -->|Invalid| D[Error Message]
    C --> E[Gemini Model]
    E --> F[Generate Mindmap JSON]
    F --> G[Save to mindmap.json]
    G --> H[Display Mindmap]
    H --> I[Log via Logfire]
```

### Output Image provided in the same folder


