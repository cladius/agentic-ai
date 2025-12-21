# LEVEL 2

## Overview
This level aims to build a **Conversational AI Agent** using Mastra and Google's Gemini model. It’s a step up from Level 1, introducing **Conversational Memory**, which lets the agent remember previous questions and answers to provide context-aware responses. For example, if you share your interests, the agent uses that context for follow-up questions. 

### What is Conversational Memory?
Conversational Memory means the agent keeps track of your conversation history (e.g., what you asked and its responses) to make answers more relevant. For instance:

> You say: "I’m Tripty, interested in compiler design and ML. What are career options?"

> The agent responds: "Careers in compiler engineering or ML research are great fits."

> You ask: "What textbooks align with my interests?"

> The agent uses the history (knowing you like compiler design and ML) to suggest: "Try 'Compilers: Principles, Techniques, and Tools' and 'Deep Learning'."


## Conversation States
In order to make conversations more meaningful and easier to navigate, an agent must be able to have recall power. Recall, here, refers to the ability to call up on past conversation in order to have continuous context of the chat. To give your agent memory simple create a memory object using class  `Memory`  from  `@mastra/memory`.

Context is broken into three parts in Mastra-

**1. Working Memory**  - All user information that is gathered over time from interactions is known as the working memory. This is key knowledge about the user that can serve an important role during new conversations. This may include the user's name, preferences or field of work.

Working memory can be found in two scopes: Thread-scoped & Resource-scoped

-   Thread-scope: Memory is stored within the session
-   Resource-scope: Memory persists across different session of a single agent(resource).

**2. Message History**  - A store of the most recent message sent by the user. This is set to 10 by default and can be changed using the parameter  `lastMessages`  in the memory's  `options`  parameter.

**3. Semantic Recall**  - When older messages are no longer in the Message History, but are relevant to the current context, a RAG-based search is used. Vector embeddings are searched based on similarity. This helps maintain context over long conversations. It is enabled by default.

## Problem Faced 
While following the documentation for working memory customization, I was faced with an error which stated that the code I had followed was invalid. The documentation agent was also not of much help; it was unable to provide exactly what I was asking for. Upon searching online, I found another method to implement the same concept, which worked.

The documentation can be faulty at some points or may leave out key details that you have to figure out yourself.


