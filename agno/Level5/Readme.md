Multi-Source Summarization and Podcast Generation
--
The l5-1.py, l5-2.py, and MultiSource Application workflows form a progressive content-to-podcast pipeline built using the Agno AI framework. These workflows extract and summarize content from sources like PDFs, YouTube videos, webpages, and plain text, converting it into engaging audio using TTS. l5-1.py is a basic monologue workflow with a single agent and minimal processing. l5-2.py enhances this with a dialogue format, two speaker agents, modular routing, and more natural audio output. The most advanced, MultiSource Application, introduces a multi-agent, multi-modal architecture with agents for podcast generation, mindmap creation, dynamic routing, and robust error handling. It also features SQLite caching, visual outputs, and detailed step tracing—making it highly extensible and production-ready.

Key Differences Between l5-1.py and l5-2.py and MultiSource Application:

| **Feature**                         | **l5-1.py (Monologue)🎙️**    | **l5-2.py (Dialogue) 🗣️🗣️**             | **MultiSource Application 🚀**                                                     |
| ----------------------------------- | ------------------------------ | ----------------------------------------- | --------------------------------------------------------------------------------------------- |
| **Podcast Style**                   | Single speaker 🧍‍♂️           | Two speakers in dialogue format 👥        | Two speakers, team-generated dialogue, TTS for each 👥🎤                                      |
| **Podcast Agent/Team**              | One agent 👤                   | Team of two speaker agents 👥👤           | Modular team: podcast agent, podcast team, audio workflow, mindmap agent, etc. 🧠🧩           |
| **Audio Segment Combination**       | Not combined ❌                 | Combined with natural pauses ⏸️✅          | Combined with natural pauses, multi-segment TTS, final MP3 ⏸️✅                                |
| **URL Extraction & Classification** | Regex-based function 🔗🧾      | Dedicated agent with JSON correction 🤖🧹 | Dedicated URL handler agent + JSON corrector agent 🤖🧹                                       |
| **Modular Agent/Team Structure**    | Basic setup 🧩                 | Advanced modular team structure 🧠🧩      | Highly modular, multi-agent, multi-team structure 🧠🧩🚦                                      |
| **Routing**                         | Manual routing in workflow 🛠️ | Team-based dynamic routing 🔄🤝           | Dynamic, multi-level routing: content type → agent/team 🔄🤝                                  |
| **Error Handling**                  | Basic try/except handling ⚠️   | Stepwise and granular error recovery 🪜✅  | Granular, stepwise error handling with logging, cache fallback, agent-level recovery 🪜✅📝    |
| **Intermediate Step Streaming**     | Limited or minimal 🔄🚫        | Extensive and transparent streaming 🌐    | Extensive streaming of intermediate steps, agent logs, and tool calls 🌐📝                    |
| **User Engagement**                 | Lower engagement 📉            | Higher engagement via natural dialogue 📈 | Highest engagement: dialogue, multi-modal output (audio, mindmap), and detailed feedback 📈🚀 |
| **Podcast Voices**                  | Single voice 🗣️               | Two distinct voices 🗣️🗣️                | Two distinct voices, configurable, TTS per speaker, combined MP3 🗣️🗣️                       |
| **Mindmap Generation**              | Not available ❌                | Not available ❌                           | Fully automated mindmap generation via agent, outputs PNG 🧠🖼️                               |
| **Caching**                         | Not available ❌                | Not available ❌                           | SQLite-based caching for prompt/response and file existence 🗄️✅                              |
| **Extensibility**                   | Low 🧩                         | Medium 🧩🧩                               | High: easily add new agents, teams, workflows, and tools 🧩🧩🧩                               |




l5-1:
--
l5-1.py is an advanced workflow script that demonstrates multi-source summarization and podcast generation using the Agno framework, Gemini language model, and various AI tools.

What does this file do?

1. Loads environment variables and API keys from a .env file for secure configuration.
2. Classifies and processes multiple content sources from a user prompt, including:
    - PDFs: Downloads, chunks, and summarizes PDF content using a vector database and Gemini embeddings.
    - YouTube videos: Fetches and summarizes video transcripts.
    - Webpages: Scrapes and summarizes webpage content.
    - Plain text: Summarizes any remaining text in the prompt.
3. Combines all summaries into a single, concise output.
4. Optionally generates a podcast (audio file) from the combined summary using ElevenLabs voice synthesis if requested by the user.
5. Handles errors and retries with exponential backoff for robust scraping and summarization.
6. Provides an interactive Agno Playground web UI for users to input prompts, view summaries, and download generated podcasts.

How to use
1. Install dependencies - *pip install agno chromadb google-genai python-dotenv opentelemetry-sdk*
2. Set up your environment
- Create a .env file in the project directory and add your API keys:
      GOOGLE_API_KEY=your_google_api_key
  
      ELEVEN_LABS_API_KEY=your_elevenlabs_api_key
  
      LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
  
      LANGFUSE_SECRET_KEY=your_langfuse_secret_key
3. Run the script- *python l5-1.py*
4. Open the web interface :Follow the instructions in the terminal to access the Agno Playground and interact with the multi-source summarization and podcast workflow.

Customization:
- Add or modify agent instructions to tailor summaries for your use case.
- Change the voice or model settings for podcast generation.
- Adjust retry and backoff logic for different reliability needs.

Dependencies
- agno
- chromadb
- google-genai
- python-dotenv
- opentelemetry-sdk
- elevenlabs (for podcast audio)

This script is ideal for building an AI-powered assistant that can summarize content from multiple sources and generate podcasts, all through a single conversational interface.


l5-2:
--
l5-2.py is a comprehensive workflow script that demonstrates multi-source content extraction, summarization, and podcast generation using the Agno framework, Gemini language model, and a team of specialized AI agents.

What does this file do?
1. Loads environment variables and API keys from a .env file for secure configuration.
2. Extracts and classifies content sources from user prompts, including:
    - PDFs: Downloads, chunks, and summarizes PDF content using a vector database and Gemini embeddings.
    - YouTube videos: Fetches and summarizes video transcripts.
    - Webpages: Scrapes and summarizes webpage content.
    - Plain text: Summarizes any remaining text in the prompt.
3. Combines all summaries into a single, concise output.
4. Optionally generates a podcast (audio file) from the combined summary using ElevenLabs voice synthesis, with a simulated conversation between two speakers.
5. Handles errors and retries with exponential backoff for robust scraping and summarization.
6. Provides an interactive Agno Playground web UI for users to input prompts, view summaries, and download generated podcasts.
7. Includes modular agents and teams for each content type, with stepwise error reporting and JSON validation for robust evaluation and debugging.

How to use
1. Install dependencies : *pip install agno chromadb google-genai python-dotenv pydub*
2. Set up your environment

   Create a .env file in the project directory and add your API keys:

       GOOGLE_API_KEY=your_google_api_key
      
       ELEVEN_LABS_API_KEY=your_elevenlabs_api_key  

3. Run the script
4. Open the web interface :Follow the instructions in the terminal to access the Agno Playground and interact with the multi-source summarization and podcast workflow.

Evaluation and Debugging
1. Structured JSON validation: Ensures all extracted and classified URLs and content are valid and well-structured before further processing.
2. Stepwise error reporting: Each stage (URL extraction, classification, content processing, audio generation) logs warnings and errors, which are returned to the user for transparency.
3. Intermediate step streaming: The workflow streams intermediate steps and agent responses, making it easy to debug and evaluate each part of the process.
4. Team-based routing: By routing tasks to specialized agents (for PDFs, YouTube, web, text, and podcast generation), the workflow enables granular evaluation of each content type and processing step.
5. Podcast generation evaluation: The podcast conversation is parsed, segmented, and synthesized into audio, with each segment and the final output checked for success and logged for review.

Dependencies
- agno
- chromadb
- google-genai
- python-dotenv
- pydub
- elevenlabs (for podcast audio)

This script is ideal for building, evaluating, and debugging AI-powered assistants that can summarize content from multiple sources and generate podcasts, all through a single conversational interface. The modular agent design and stepwise evaluation make it easy to monitor and improve each stage of the workflow.

MultiSource Application
--
The MultiSource Application folder is the pinnacle of the Agno framework’s evolution, offering a sophisticated, extensible, and production-ready system for automated content processing, summarization, and multi-modal output generation. This architecture is designed to handle complex, real-world workflows involving diverse content types and output formats, making it ideal for research, content creation, education, and knowledge management.

Key Features:

1. Multi-Agent & Team-Based Architecture
    - Specialized Agents: Each agent is responsible for a distinct task (e.g., URL extraction, JSON correction, web scraping, summarization, podcast dialogue generation, mindmap creation).
    - Team Collaboration: Agents can be grouped into teams for complex workflows, enabling parallel processing and dynamic task assignment.
    - Separation of Concerns: Modular design allows for easy maintenance, testing, and the addition of new capabilities.
2. Advanced Podcast Generation
    - Dialogue Format: Generates podcasts as natural, two-speaker conversations, enhancing engagement and clarity.
    - Text-to-Speech (TTS): Assigns unique, configurable voices to each speaker using TTS synthesis.
    - Audio Combination: Segments are combined with natural pauses and transitions, resulting in a professional-quality MP3 output.
    - Automated Workflow: From content extraction to final audio file, the process is fully automated.
3. Automated Mindmap Generation
    - Visual Summarization: Converts text topics into comprehensive, hierarchical mindmaps.
    - Graphviz Integration: Uses Python and Graphviz to render clear, visually appealing PNG diagrams.
    - Seamless Output: Mindmaps are generated and saved automatically, ready for sharing or embedding.
4. Dynamic Routing & Workflow Management
    - Content-Type Detection: Automatically identifies the type of input (PDF, YouTube, web, text) and routes it to the appropriate agent or team.
    - Flexible Output Selection: Supports multiple output formats (podcast, mindmap, text summary) based on user request or workflow configuration.
    - Scalable Design: Easily adapts to new content types or output modalities.
5. Robust Error Handling & Logging
    - Stepwise Recovery: Each workflow stage includes granular error handling, allowing for graceful recovery or fallback strategies.
    - Comprehensive Logging: Detailed logs provide transparency, facilitate debugging, and support auditability.
6. Efficient Caching
    - SQLite-Based Cache: Stores prompt/response pairs and file existence checks to avoid redundant processing and speed up repeated tasks.
    - Smart Invalidation: Ensures cache consistency and up-to-date outputs.
7. Extensibility & Customization
    - Plug-and-Play Agents: Easily add or replace agents and teams to support new tasks or integrate with external APIs.
    - Configurable Workflows: Adapt workflows to specific use cases or organizational needs.
8. Playground Integration
    - Interactive Testing: Includes a playground app for experimenting with workflows, visualizing outputs, and rapid prototyping.
    - Real-Time Feedback: See intermediate and final results instantly, aiding development and debugging.
9. Typical Workflow
    - Input Acquisition:
        - Accepts content from PDFs, YouTube videos, web pages, or plain text.
        - Content Extraction & Summarization:
        - Specialized agents extract, clean, and summarize the core information.
    - Dynamic Routing:
        - The system determines the appropriate workflow (podcast, mindmap, etc.) based on user input or content analysis.
    - Output Generation:
        - Podcast: Generates a dialogue script, synthesizes audio for each speaker, and combines segments into a single MP3.
        - Mindmap: Creates a visual diagram and saves it as a PNG.
10. Caching & Logging:
    - Results are cached for efficiency, and all steps are logged for transparency.
11. Output Delivery:
    - Provides the final audio file or mindmap image to the user.
12. Use Cases
    - Educational Content Creation:
        - Convert lecture notes, articles, or research papers into engaging podcasts and visual mindmaps for students and educators.
    - Research Summarization:
        - Summarize and visualize complex research findings for easier understanding, collaboration, and dissemination.
    - Content Repurposing:
        - Transform existing content into new formats (audio, visual) for broader reach and accessibility.
    - Knowledge Management:
        - Automate the organization, summarization, and visualization of large volumes of information for teams and organizations.

Folder Structure Overview

agents/ – Specialized agents for tasks like extraction, summarization, podcast generation, mindmap creation, etc.

teams/ – Agent teams for collaborative workflows.

workflows/ – Definitions of end-to-end workflows (podcast, mindmap, etc.).

cache/ – SQLite database and cache management utilities.

playground/ – Interactive app for testing and prototyping.

utils/ – Utility functions and helpers.


OUTPUT:
--
WebPage:(https://notebooklm.google)
![image](https://github.com/user-attachments/assets/3bf20df3-6ee6-402f-ad09-f0f0a414b296)

YouTube Video: (https://youtu.be/69tPv5xZJjc)
![image](https://github.com/user-attachments/assets/01b38e08-7357-4ebb-bf82-9c7787cc9b36)

PDF : (https://www.adobe.com/support/products/enterprise/knowledgecenter/media/c4611_sample_explain.pdf)
![image](https://github.com/user-attachments/assets/61004c82-f4e5-4468-aee0-256be1821b25)

Plain Text:
![image](https://github.com/user-attachments/assets/261c7629-8b04-4c48-9aab-af4754c20243)

MindMap Example :
![mindmap_output](https://github.com/user-attachments/assets/773d0649-2bef-453e-9951-bfec07a91ac0)
