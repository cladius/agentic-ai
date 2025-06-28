MultiSource Application
--
The MultiSource Application is a comprehensive, modular system designed for advanced content processing, analysis, and visualization using multi-agent workflows and AI-powered tools. It is ideal for research, educational, and automation projects that require extracting insights from diverse sources such as web pages, PDFs, YouTube videos, and plain text.

**Folder Structure & Components:**
1. main.py : The entry point for the application. Launches the playground app and initializes the multi-source workflow system.
2. workflow/ : Contains the core logic for orchestrating the multi-agent workflow. Handles routing, task assignment, and coordination between agents for processing different content types.
3. agents/ : Houses specialized agents, each responsible for a specific task:
    - URL Agent: Extracts and classifies URLs from input.
    - Web Scraper Agent: Scrapes and processes web page content.
    - PDF Agent: Extracts and summarizes text from PDF files.
    - YouTube Agent: Processes YouTube links, extracts transcripts, and summarizes content.
    - Text Agent: Handles plain text input for summarization and analysis.
    - JSON Correction Agent: Ensures output is valid and corrects malformed JSON.
    - Mindmap Agent: Generates mindmaps from summarized content.
    - Podcast Agent: Creates podcast-style conversations and synthesizes audio.
4. teams/ : Defines collaborative teams of agents for complex tasks, such as:
    - Podcast Team: Simulates a multi-agent podcast discussion on a given topic.
    - Multi-Source Team: Coordinates agents to process and merge information from various sources.
5. utils/ : Utility modules for supporting tasks, such as audio processing, file handling, and caching.

**Features:**
1. Multi-Source Content Processing: Seamlessly extracts, classifies, and processes content from URLs, PDFs, YouTube videos, and plain text.
2. Agent-Based Modular Architecture: Each agent is designed for a specific function, making the system highly modular and easy to extend.
3. AI-Powered Summarization & Analysis: Integrates Google Gemini models for advanced summarization, topic extraction, and content analysis.
4. Mindmap Generation: Automatically creates mindmaps (PNG images) to visualize the structure and relationships within complex topics.
5. Podcast Generation: Simulates podcast conversations on any topic and generates audio using ElevenLabs and Google Gemini.
6. Caching & Efficient Storage: Uses SQLite to cache workflow responses, reducing redundant processing and improving performance.
7. Extensible Teamwork: Teams of agents can be easily configured for collaborative tasks, supporting scalable and flexible workflows.

**How to Use:**
1. Install Dependencies:
   - graphviz (for mindmap generation)
   - requests (for web requests)
   - beautifulsoup4 (for web scraping)
   - Elevenlabs (for podcast audio synthesis)
   - sqlite3 (for caching, usually part of Python standard library)
   - python-dotenv (for loading environment variables)
   - pydub or soundfile (for audio processing)

2. Set Up Environment Variables: Create a .env file in the root directory with your API keys for Google Gemini and ElevenLabs.
3. Run the Main Application: *python main.py*

**Example Use Cases:**
1. Educational Tools: Visualize and summarize complex topics for students and educators.
2. Research Automation: Aggregate and analyze information from multiple sources for literature reviews or knowledge synthesis.
3. Podcast Creation: Automatically generate podcast scripts and audio on trending topics or research areas.
4. Content Summarization: Quickly extract key insights from large documents, videos, or web pages.

**Notes:**

The system is designed for extensibility. You can add new agents, teams, or workflows as needed.

Ensure you have the necessary API keys for all integrated services.

Mindmap scripts require Graphviz to be installed on your system
