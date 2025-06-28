**1. Built-in:**
--
*built-in.py* is an example script that demonstrates how to create a conversational AI agent with built-in memory using the agno framework and the Gemini language model.

What does this file do?
1. Loads environment variables (including your Google API key) for secure configuration.
2. Initializes an AI agent ("Built-In Memory Agent") with the Gemini model, enabling:

   i. Built-in memory to include previous chat history in conversations.

   ii. Contextual awareness by specifying how many previous responses to remember.

   iii. A positive, polite assistant persona via a custom description.

   iv. Creates a web-based playground app for interactive conversations with the agent.
   
3. Runs the playground server so you can chat with the memory-enabled agent in your browser.
4. How to use

      Add your GOOGLE_API_KEY to a .env file in the project directory.

      Run the script: *python built-in.py*

Open the provided web interface to interact with the agent and experience its conversational memory.
This file is a practical starting point for building context-aware conversational agents with memory using agno and Gemini.
   
   ![image](https://github.com/user-attachments/assets/4d0e8de5-207f-46bd-8f18-1660df049933)

**2. Built-in-cli:**
--
*built-in-cli.py* is a command-line example that demonstrates how to interact with a conversational AI agent with built-in memory using the agno framework and the Gemini language model.

What does this file do?
1. Loads environment variables (including your Google API key) for secure configuration.
2. Initializes an AI agent with:

   i. The Gemini model for language understanding.

   ii. Built-in memory to include previous chat history in conversations.

   iii. Contextual awareness by specifying how many previous responses to remember.

   iv. A positive, polite assistant persona via a custom description.

   v. Monitoring and markdown formatting enabled.

   vi. Prompts the agent with a message and streams the response in the terminal.

   vii. Prints the agent’s memory (conversation history) after each interaction for transparency.

   viii. Demonstrates follow-up questions and how the agent uses memory to answer contextually.
   
3. How to use

   Add your GOOGLE_API_KEY to a .env file in the project directory.

   Run the script: *python built-in-cli.py*
   
4. Interact with the agent and observe how it remembers and responds to previous messages.
   
This file is a practical starting point for building and testing memory-enabled conversational agents in a command-line environment using agno and Gemini.

   ![image](https://github.com/user-attachments/assets/79b74ba1-279c-4dc1-ae75-9e0002b50cf1)
   ![image](https://github.com/user-attachments/assets/7e5c61a5-0f11-407f-8b3b-8ab463159594)

**3. Session-storage:**
--
*session-storage.py* is an example script that demonstrates how to create a conversational AI agent with persistent session memory using the agno framework and the Gemini language model.

What does this file do?
1. Loads environment variables (including your Google API key) for secure configuration.
2. Initializes an AI agent ("SessionStorageAgent") with:

   i. The Gemini model for language understanding.

   ii. Persistent conversation memory using SQLite, so chat history is saved across sessions and script restarts.

   iii. A fixed session ID to ensure continuity of the same conversation over multiple runs.

   iv. Contextual awareness by including previous chat history in the model input.

3. Creates a web-based playground app for interactive conversations with the agent.
4. Runs the playground server so you can chat with the agent and experience persistent memory in your browser.
5. How to use

   Add your GOOGLE_API_KEY to a .env file in the project directory.

   Run the script:

6. Open the provided web interface to interact with the agent and see how it remembers previous conversations, even after restarting the script.

This file is a practical starting point for building persistent, context-aware conversational agents using agno, Gemini, and SQLite storage.

   ![image](https://github.com/user-attachments/assets/a2ea5401-b856-425f-b763-bf1b9dd7abcb)
   ![image](https://github.com/user-attachments/assets/26b5e17b-0f25-483e-9044-11b9016652bf)

**4. session-storage-cli:**
--
*session-storage-cli.py* is a command-line example that demonstrates how to create a conversational AI agent with persistent session memory using the agno framework and the Gemini language model.

What does this file do?
1. Loads environment variables (including your Google API key) for secure configuration.
2. Initializes an AI agent ("Session Storage Agent") with:

   i. The Gemini model for language understanding.

   ii. Persistent conversation memory using SQLite, so chat history is saved across sessions and script restarts.

   iii. A fixed session ID to ensure continuity of the same conversation over multiple runs.

   iv. Contextual awareness by including previous chat history in the model input.

   v. Monitoring, markdown formatting, and streaming enabled for better debugging and output.

   vi. Prompts the agent with a question and a follow-up to demonstrate memory.

   vii. Prints the agent’s session memory (conversation history) in the terminal for transparency.
3. How to use

   Add your GOOGLE_API_KEY to a .env file in the project directory.

   Run the script: *python session-storage-cli.py*
   
4. Interact with the agent and observe how it remembers previous messages, even after restarting the script.

This file is a practical starting point for building persistent, context-aware conversational agents in a command-line environment using agno, Gemini, and SQLite storage.

   https://github.com/user-attachments/assets/0e7c44b3-3b6f-43b7-860c-f97a49143afa

**5. user-memory:**
--
*user-memory.py* is an advanced example demonstrating how to build a conversational AI agent with both persistent session memory and user-specific long-term memory using the agno framework and the Gemini language model.

What does this file do?
1. Loads environment variables (including your Google API key) for secure configuration.
2. Sets up two types of memory:

   i.User-specific memory: Stores long-term user information in a dedicated SQLite database.

   ii. Session (conversation) memory: Stores chat history in a separate SQLite database for persistent context across sessions.
   
4. Initializes an AI agent ("UserMemoryAgent") with:

   i. The Gemini model for language understanding.

   ii. Both user and agent memory enabled for richer, more personalized conversations.

   iii. Contextual awareness by including previous chat history in the model input.

   iv. Markdown formatting, streaming responses, and session summaries enabled.

5. Creates a web-based playground app for interactive conversations with the agent.
6. Runs the playground server so you can chat with the agent and experience both persistent and user-specific memory in your browser.
7. How to use

   Add your GOOGLE_API_KEY to a .env file in the project directory.

   Run the script:*python user-memory.py*

8. Open the provided web interface to interact with the agent and see how it remembers both session and user-specific information.

This file is a practical starting point for building highly personalized, context-aware conversational agents using agno, Gemini, and advanced memory management.

   ![image](https://github.com/user-attachments/assets/e02bad5a-22ff-41a4-b979-f56abe5a9129)
   ![image](https://github.com/user-attachments/assets/42252f89-8939-40ee-a6b0-b491c5381de0)

**6. user-memory-cli:**
--
*user-memory-cli.py* is an advanced command-line example that demonstrates how to build a conversational AI agent with both persistent session memory and user-specific long-term memory using the agno framework and the Gemini language model.

What does this file do?
1. Loads environment variables (including your Google API key) for secure configuration.
2. Sets up two types of memory:

   i. User-specific memory: Stores long-term user information in a dedicated SQLite database.

   ii. Session (conversation) memory: Stores chat history in a separate SQLite database for persistent context across sessions.
3. Initializes an AI agent ("UserMemoryAgent") with:

   i. The Gemini model for language understanding.

   ii. Both user and agent memory enabled for richer, more personalized conversations.

   iii. Contextual awareness by including previous chat history in the model input.

   iv. Markdown formatting, streaming responses, intermediate step streaming, and monitoring enabled.

4. Includes a helper function to prompt the agent and throttle requests, allowing time for memory updates and avoiding rate limits.
5. Demonstrates a sequence of interactions to show how the agent remembers, updates, and deletes user-specific information.
6. How to use

   Add your GOOGLE_API_KEY to a .env file in the project directory.

   Run the script:*python memory-user-cli.py*
   
7. Interact with the agent in your terminal and observe how it remembers and manages both session and user-specific information.

This file is a practical starting point for building highly personalized, context-aware conversational agents in a command-line environment using agno, Gemini, and advanced memory management.

   ![image](https://github.com/user-attachments/assets/c45a812f-72cc-46e5-922d-06934ce16135)
   ![image](https://github.com/user-attachments/assets/9fc6c99f-a395-48c0-b8e5-f081db019bba)
   ![image](https://github.com/user-attachments/assets/5738eac2-3891-45ac-a885-f6b954c6c215)
   ![image](https://github.com/user-attachments/assets/9907250f-51d2-4d71-8596-9e4979ec3347)
   ![image](https://github.com/user-attachments/assets/700be53e-c1c9-4087-83b1-e1a1e25a53f1)
   ![image](https://github.com/user-attachments/assets/8edc5b33-488b-41f4-a2fa-b54739fc9b76)






   
   
