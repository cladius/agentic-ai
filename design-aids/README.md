Designing an agentic AI system involves a structured approach, starting with detailing how users interact with the system and then specifying the agents and tools that will fulfill these interactions. This design phase precedes any coding or implementation.

Here are the detailed steps, focusing on the User-System Interaction Document and the Agent Specification Document:

### 1. User-System Interaction Document (e.g., `Interaction.md`)

This document outlines **how the agentic AI system will interact with human users**. It helps in clarifying the system's requirements and desired behavior from the user's perspective.

**Steps to Create:**
1.  **Define User Personas**: Start by identifying the different types of users who will interact with the system. For each persona, detail their background, experience (e.g., experienced with AWS), knowledge, access levels, and goals. This helps in understanding who the system is being designed for.
2.  **Detail Interaction Workflows**:
    *   **Happy Paths**: Describe typical, successful interactions between the user and the system. This involves outlining the user's input and the system's subsequent actions and responses in a conversational, step-by-step manner.
        *   **Example**: If a user navigates to say an Amazon.com product page for a book and asks "Is there a hardcover?", the document would detail:
            *   **User**: (Navigates to URL and launches AI) "Is there a hardcover?"
            *   **AI (Thinking...)**: "The system will look up the product information. The system will look for product variants. It will make an LLM call. And then present that answer to the user."
            *   **AI**: "Yes. There is a hardcover."
        *   Each "thought" or "action" by the system should be an atomic, discrete step (e.g., "make an LLM call," "make a tool call," "retrieve something from a database," "access something on the file system").
    *   **Edge Cases and Failures**: Document how the system should handle unexpected inputs, errors, or limitations. The system should provide feedback to the user, such as "I failed to draft the email" or "Your API key was incorrect," so the user can address the issue.
3.  **Format**: The document can be written as a narrative, resembling a chat history, using clear language (e.g., "User: said this, System: thought about this, System: did this, System: responded with this"). Markdown files (e.g., `Interaction.md`) are suitable for this.

This document provides a clear understanding of **"what" the system should do** before moving on to "how" it will be built.

### 2. Agent Specification Document (e.g., `AgentSpec.md`)

Once the user-system interactions are clearly defined, the next step is to detail the internal components of the agentic system: the agents themselves, their roles, responsibilities, and the tools they will use.

**Steps to Create:**
1.  **Identify Agents**: Based on the interaction workflows, determine the distinct agents needed. Each agent should have a **very specific goal and responsibility**. Avoid creating overly broad agents.
2.  **Define Each Agent's Details**: For each identified agent, create a section with the following:
    *   **Agent Name**: Assign a descriptive name based on its primary function (e.g., "Planner Agent," "Email Agent," "JIRA Agent," "AWS Infra Agent").
    *   **Role**: Provide a concise, **one-to-two-line summary** of the agent's core purpose. This is the decision-making part of the agent, often powered by an LLM.
        *   **Example for a Planner Agent**: "Make a plan using the available agents to service the user's request - powered by an LLM."
    *   **Responsibilities**: List the specific tasks the agent is expected to perform in a bulleted format. These should be directly inferable from the user-system interaction flows.
        *   **Example for a Planner Agent**:
            *   Ask the user for clarification on requests.
            *   Present the plan to the user for approval & edits.
            *   Prepare a detailed plan.
            *   Invoke other agents in sequence according to the plan.
            *   Inform the user about the final successful output.
            *   Inform the user about any errors.
    *   **Capabilities and Boundaries**: Clearly define what the agent **can do** and, importantly, what it **cannot do**. This sets explicit limits to prevent unintended actions.
        *   **Example**: An agent connected to a database might "only be able to do reads," "can't do writes," or "can't do deletes/drops".
    *   **Tools**: List the specific tools that the agent will be equipped with to perform its responsibilities. Each tool should be **very specific and perform one distinct function**.
        *   **Example for a Planner Agent**:
            *   Access Pre-curated plans.
            *   Invoke other agents as tools.
            *   Interact with user.
        *   A tool should not be bloated (e.g., "send email" is good, "send email and connect to database" is not). Tools can be built-in (prebuilt libraries) or custom-written.
3.  **Format**: This document can also be created as a Markdown file (e.g., `AgentSpec.md`) for clear structure and easy readability.

By developing these two documents, you establish a **solid blueprint for your agentic AI system**, ensuring mental clarity and a well-defined scope before proceeding to the implementation phase. It is recommended to keep these documents in a Git repository and share them for feedback.
