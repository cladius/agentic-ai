Evaluation
--
This is an advanced example script that demonstrates how to orchestrate a team of AI agents for web search, synthesis, and automated evaluation using the Agno framework and the Gemini language model.

What does this file do?
1. Loads environment variables (including your Google API key) for secure configuration.
2. Defines a multi-agent team:

      i. Query Reformulator Agent: Improves user queries for more effective searching.
    
      ii. Web Searcher Agent: Uses DuckDuckGo tools to search the web for relevant information.
    
      iii. Answer Synthesis Agent: Synthesizes information from multiple articles into a coherent answer.

3. Coordinates these agents as a team using the Team class, so each agent performs its task in sequence, passing results to the next.
4. Enables advanced features such as tool usage visibility, markdown formatting, debug mode, and sharing of context/history among agents.
5. Provides a web-based playground app for interactive experimentation with the agent team.

**Automated Evaluation**

A key feature of this script is the use of the AccuracyEval class to automatically evaluate the performance of the agent team:
1. Defines an evaluation scenario with a specific input question and an expected output description.
2. Runs the evaluation by having the team answer the question and comparing the response to the expected output.
3. Prints evaluation results for transparency and debugging, helping you measure the quality and relevance of the team’s answers.
4. This enables you to benchmark and iterate on your multi-agent workflows with real, automated feedback—making it easier to improve your AI system’s accuracy and reliability.

How to use
1. Install dependencies: *pip install agno chromadb google-genai python-dotenv*
2. Set up your environment

      Create a .env file in the project directory and add your API keys: *GOOGLE_API_KEY=your_google_api_key*
    
      Run the script: *python web-teams.py*

3. View the evaluation results : The script will print the evaluation outcome in the terminal.
4. Open the web interface : Access the Agno Playground to interact with the agent team in real time.

Dependencies
- agno
- google-genai
- python-dotenv

This script is ideal for building, testing, and evaluating collaborative AI agent workflows for complex information retrieval and synthesis tasks.

**OUTPUT**:

![image](https://github.com/user-attachments/assets/03c88862-0b39-44b3-8d8c-f39b9a3038ad)
