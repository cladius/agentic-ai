# Level 1: Basic LangChain4j Agent

This module demonstrates a minimal LangChain4j integration in Java. It sets up a single-agent interface that communicates with an OpenAI-compatible LLM endpoint to simulate a basic "Hello World" interaction.

---

## What It Does

- Uses LangChain4j to define an AI-powered interface (`Assistant`) via annotations.
- Connects to an OpenAI-compatible backend (demo endpoint) using the `OpenAiChatModel`.
- Accepts real-time user input from the terminal.
- For each user message, generates a single-shot LLM response using the specified model.

This level does **not** include memory, tools, or advanced flow control. Each interaction is stateless and independent.

---

## Key Technologies

- **Java 17**
- **LangChain4j Core**
- **LangChain4j OpenAI Integration**
- **Maven** (for dependency and project management)

---

## How It Works

1. **Annotated Interface**: The `Assistant` interface defines how the AI will be invoked. It uses `@SystemMessage` to set context, and `@UserMessage` to define user input.

2. **Model Configuration**: A mock OpenAI-compatible chat model is created using the builder pattern. This simulates interaction without requiring real API keys.

3. **AI Binding**: LangChain4j uses `AiServices.create()` to bind the interface to the model, dynamically generating the implementation.

4. **Interactive Loop**: A `Scanner` captures user input from the terminal. Each input is sent to the model, and the result is printed back.

---

## How To Run

1. Ensure you have Java 17+ and Maven installed.
2. Navigate to this module (`Level1`) in your terminal.
3. Run the app via IntelliJ or Maven:
   ```bash
   mvn clean compile exec:java -Dexec.mainClass="com.langchain4j.level1.Main"

---

## Challenges Faced

**1. Understanding LangChain4j’s Design Patterns**  
As someone new to LangChain4j, it took some time to understand how the framework relies on annotations like `@SystemMessage` and `@UserMessage` to define AI behavior. The approach of interacting with language models through annotated interfaces was quite different from traditional Java paradigms.

**2. Limited Beginner-Oriented Documentation**  
The available documentation is still evolving and tends to assume prior familiarity with LLM concepts and architecture. As a newcomer, I often had to rely on scattered GitHub examples and trial-and-error experimentation to piece things together.

**3. Ambiguity in Model Configuration**  
Although the project used a demo OpenAI-compatible endpoint, configuring the model correctly was not straightforward. Details like which fields were required (e.g., `apiKey`, `baseUrl`) and where to specify them were not always clear. Misconfiguration often led to vague or unhelpful error messages.

**4. Runtime Error Handling and Debugging**  
Because LangChain4j generates the implementations of annotated interfaces at runtime, there was no compile-time validation. When something failed, the exceptions typically originated from within the library internals, making it challenging to trace the actual issue.

**5. Maven Build and Execution Friction**  
Setting up the Maven environment to build and run the project required additional attention. Configuring the `exec-maven-plugin`, managing dependencies, and ensuring the correct classpath setup were not trivial tasks for a first-time LangChain4j integration.

---

