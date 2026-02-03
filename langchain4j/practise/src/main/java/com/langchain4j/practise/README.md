# LangChain4j Agent with External MCP Tool

This project demonstrates an AI agent built with **LangChain4j** that uses an external tool for calculations. The tool is provided by a separate Node.js server that communicates with the Java application via the **Model-Component-Protocol (MCP)**.

The agent is instructed to delegate all addition tasks to this external tool, showcasing how LangChain4j can orchestrate interactions between a Large Language Model (LLM) and external services.

## Prerequisites

Ensure you have the following software installed on your system:

* **Java Development Kit (JDK)**: Version 17 or newer
* **Apache Maven**: To build and manage the Java project
* **Node.js and npm**: To run the external tool server
* **Git**: To clone the server repository

***

## Setup and Execution

This project requires two separate components to be running: the **MCP Tool Server** and the **Java AI Client**. You must start the server first.

### 1. Run the MCP Tool Server

The server provides the `add` tool that the AI agent will use.

1.  **Clone the Repository**
    Clone the official MCP servers repository.
    ```bash
    git clone [https://github.com/modelcontextprotocol/servers.git](https://github.com/modelcontextprotocol/servers.git)
    ```

2.  **Navigate to the Server Directory**
    ```bash
    cd servers/src/everything/
    ```

3.  **Install Dependencies**
    ```bash
    npm install
    ```

4.  **Build the Server**
    The TypeScript code must be compiled into JavaScript.
    ```bash
    npm run build
    ```

5.  **Start the Server**
    Run the Server-Sent Events (SSE) version of the server. It will listen on `localhost:3001`.
    ```bash
    node dist/sse.js
    ```
    Keep this terminal open. You should see a message confirming that the server is running on port 3001.

### 2. Run the Java AI Client

With the server running, you can now start the Java client.

1.  **Build the Project**
    From the root directory of your Java project, run the Maven build command.
    ```bash
    mvn clean install
    ```

2.  **Run the Application**
    Execute the `main` method in the `Http.java` class from your IDE or using Maven.

***

## How to Interact

Once the client application is running, it will prompt you for input. To test the tool integration, ask a question that requires addition.

**Example Interaction:**

```
=== LangChain4j Agent with HTTP MCP Tools & Memory ===
Type 'exit' to quit.

You: What is 234 + 567?
AI: The sum of 234 and 567 is 801.
```

By observing the logs in both the server and client terminals, you can verify that the LLM delegated the calculation to the Node.js server via the MCP client.