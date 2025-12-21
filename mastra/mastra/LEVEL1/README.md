# LEVEL 1

## Overview
This level involves creating a basic AI agent by incorporating an LLM. The agent interaction takes place using the playground provided by Mastra. 


## Selecting a model
Mastra makes use of the Vercel AI SDK to integrate LLMs to their workflows. The AI SDK uses routing layers so that all LLMs(from different providers) can be implemented with similar syntax.

However, only a select few providers are currently maintained by the AI SDK team. These are known as  **Official Providers.**

Other LLMs may be supported using  **Community Providers**  (e.g- Ollama models)

The model selected for this project is Gemini 1.5 pro. Google AI provides $300 of free credits before billing you, much more than anthropic and openAI's $5 credits.

Additionally, Google AI LLMs are found to be more efficient and accurate especially when integrating with other google ecosystems. Which is my aim for this agent.

## Creating the base agent
In order to create the base agent, first we create the project folder using the  `npm create mastra@latest`  command.

in the source file, within the agents folder, create an instance of the Agent class. Define the properties(model etc.) of the agent inside this instance.

This instance is called inside the index.ts template file provided by Mastra.

## Set up

In the .env file create the `GOOGLE_GENERATIVE_AI_API_KEY` variable and add your API key
