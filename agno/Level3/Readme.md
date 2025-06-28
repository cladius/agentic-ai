**web-teams:**
--
web-teams.py is an example of orchestrating multiple AI agents as a collaborative team to perform advanced web search and synthesis tasks using the agno framework.

What does this file do?

1. Loads environment variables (including the Google API key) for secure configuration.

2. Defines three specialized agents:

    i. Query Reformulator Agent: Improves user queries for more effective searching.
   
    ii. Web Searcher Agent: Uses DuckDuckGo tools to search the web based on the reformulated query.
   
    iii. Answer Synthesis Agent: Synthesizes information from multiple articles into a coherent answer.
   
3. Coordinates these agents as a team using the Team class, so each agent performs its task in sequence, passing results to the next.
4. Enables advanced features such as tool usage visibility, markdown formatting, debug mode, and sharing of context/history among agents.
5. Provides a web-based playground app for interactive experimentation with the agent team.
6. How to use:

   Make sure you have a .env file with your GOOGLE_API_KEY.

   Run the script: *python web-teams.py*
8. Open the provided web interface to interact with the multi-agent web search and synthesis workflow.

This file demonstrates how to build modular, collaborative AI workflows for complex information retrieval and summarization tasks.

OUTPUT:
![image](https://github.com/user-attachments/assets/8c766f3e-cd50-4e10-9492-cb93df02732e)

CLI:
![image](https://github.com/user-attachments/assets/b74a8f84-25de-49f3-8f1f-29452edcbaa7)
![image](https://github.com/user-attachments/assets/288367b6-7393-4af4-9db5-d8b6e41514a4)

**websearch:**
--
websearch.py is a sample script demonstrating how to build an AI-powered web search agent using the agno framework.

What does this file do?
1. Loads environment variables (including your Google API key) for secure configuration.
2. Creates a single AI agent (WebSearchAgent) that:
   
    i. Uses the Gemini language model for understanding and generating responses.
   
    ii. Integrates DuckDuckGo search tools to fetch real-time web results.
   
    iii. Streams responses and intermediate reasoning steps for transparency.
   
    iv. Supports markdown formatting and monitoring for debugging.
   
3. Launches an interactive web playground where you can chat with the agent and see how it performs live web searches and reasoning.
4. How to use

    Add your GOOGLE_API_KEY to a .env file in the project directory.

    Run the script: *python websearch.py*
5. Open the provided web interface to interact with the web search agent.

This file is a practical example of combining LLMs with web search tools for real-time, interactive information retrieval.

OUTPUT:
![image](https://github.com/user-attachments/assets/29b94b21-5a13-4ba5-a077-78f21d78f175)
