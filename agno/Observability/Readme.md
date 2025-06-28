Langfuse
--
langfuse.py is an example script demonstrating how to enable advanced observability and tracing for AI agent interactions using Langfuse and OpenTelemetry with the agno framework and Gemini language model.

What does this file do?
1. Loads environment variables (including Google API key and Langfuse credentials) from a .env file for secure configuration.
2. Configures OpenTelemetry tracing to export agent traces to Langfuse for monitoring and analytics.
3. Instruments the agno framework so all agent actions and tool calls are traced and sent to Langfuse.
4. Creates a stock price agent using the Gemini model and YFinance tools, with debug mode enabled.
5. Runs a sample query ("What is the current price of Tesla?") and traces the full reasoning and tool usage to Langfuse.

How to use
1. Install dependencies : *pip install agno openinference-instrumentation-agno opentelemetry-sdk python-dotenv*
2. Set up your environment
    Create a .env file in the project directory and add your API keys:

       GOOGLE_API_KEY=your_google_api_key

       LANGFUSE_PUBLIC_KEY=your_langfuse_public_key

       LANGFUSE_SECRET_KEY=your_langfuse_secret_key

4. Run the script- *python langfuse.py*
5. View traces in Langfuse : Log in to your Langfuse dashboard to monitor and analyze the agent’s reasoning, tool usage, and responses.

Dependencies
- agno
- openinference-instrumentation-agno
- opentelemetry-sdk
- python-dotenv

This script is ideal for developers who want to add observability, debugging, and analytics to their AI agent workflows using Langfuse and OpenTelemetry.

OUTPUT:
--
![image](https://github.com/user-attachments/assets/f488dad8-6bae-43d2-94e0-9b2d94aacb4d)
