# LangChain4j Level 3: Agent with SearchApi Tool

This project demonstrates the **Level 3 LangChain4j agent** using the `SearchApiWebSearchEngine` as a tool, integrated with an `OpenAiChatModel` and basic memory. The agent is capable of performing real-time web searches for current information.

---

##  Basic Working

A command-line assistant that:

- Accepts user input.
- Determines if a web search is required.
- Uses **SearchApi** to fetch real-time web results.
- Constructs responses using **OpenAI GPT** (4-o-mini).
- Retains short-term memory using `MessageWindowChatMemory`.

---

##  Tech Stack

| Component       | Library / API                                       |
|----------------|------------------------------------------------------|
| Language        | Java                                                 |
| AI Model        | `OpenAiChatModel` (e.g., GPT-4o-mini or GPT-3.5)     |
| Web Search Tool | `SearchApiWebSearchEngine` from LangChain4j         |
| Memory          | `MessageWindowChatMemory`                            |
| Agent Binding   | `AiServices`                                         |
| CLI Input       | Java `Scanner`                                       |

---

## How to Run

### 1. Provide search api tool in the terminal as follows
#### Powershell:
```bash
   $env:SEARCHAPI_KEY="your_key"
```
#### MacOS/Linux/WSL:
```bash
   export SEARCHAPI_KEY="your_real_key_here"
```

### 2. Run
```bash
   mvn exec:java
```

### Sample Interaction

**You:** Temperature next week in Pune, also what date is it today  
**AI:** Today's date is **June 25, 2025**.

### Weather Forecast for Pune Next Week:
1. **June 26**: Expect a high of around 29°C (84°F) with a chance of afternoon rain and thunderstorms.
2. **June 27**: The temperature will remain similar, with a high of about 28°C (82°F) and still a chance for thunderstorms.
3. **June 28**: High temperatures will be around 27°C (81°F) and mostly cloudy.
4. **June 29**: Slightly cooler with highs of 26°C (79°F) and scattered thunderstorms likely.

For more detailed and updated information, you can visit:
- [Weather.com 10-Day Forecast for Pune](https://weather.com/weather/tenday/l/cc4e93311b537126218a1d9a0dc33295fd3f3d0c8fe0965a4b8eab0fb00e7d39)

Let me know if you need more information!

---
## Challenges Faced

- **Maven Dependency Conflicts**: Inconsistent behavior occurred until exact `langchain4j` versions were matched across all modules.

- **IDE Maven Recognition Delay**: IntelliJ didn’t recognize new Maven dependencies immediately, falsely indicating missing classes. Only after running `mvn compile` did the IDE resolve them, causing initial confusion over dependency correctness.

- **SearchAPI Integration**: Simply injecting the search engine didn't trigger web calls. Wrapping it inside `WebSearchTool` was essential for activation.

- **Command-Line Errors**: Blank user inputs and vague stack traces caused runtime crashes. Added input checks and used Maven's `-e`/`-X` flags to debug.

- **HashMap Usage**: Setting optional parameters for `SearchApiWebSearchEngine` required precise `HashMap` configuration, which wasn’t clearly documented.

- **System Message Tuning**: The model ignored the tool until the system prompt was explicitly directive. Took multiple iterations to get the tone right for tool invocation.




