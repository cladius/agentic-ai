# Level 2: Conversational Memory 

This module demonstrates a stateful LangChain4j agent that remembers previous messages. It builds upon Level 1 by introducing chat memory, enabling coherent, context-aware multi-turn conversations with a single agent.

---

## What It Does

- Defines an `Assistant` interface annotated to control system and user messages.
- Leverages LangChain4j's memory interface (`MessageWindowChatMemory`) to track conversation history.
- Connects to a demo OpenAI-compatible endpoint using `OpenAiChatModel`.
- Accepts real-time user input via terminal.
- Responds with memory-aware outputs based on recent user messages.

This is a stateless LLM wrapped with local memory for short-term retention (last 10 messages).

---
## How to Run:
1. Run cmd in terminal window:
```bash
   mvn clean compile exec:java

```
## Example Interaction

**You**: Hey im preparing for JEE in Pune  
**AI**: That's great! How is your preparation going? Are you focusing on any particular subjects or topics right now? If you need any tips or resources, feel free to ask!

**You**: How old was alexander the great when he died?  
**AI**: Alexander the Great died at the age of 32. He was born in July 356 BC and died in June 323 BC. His early death came after an impressive career of military conquests and empire building. If you have more questions about him or other historical figures, feel free to ask!

**You**: what books should i buy to prepare for my exams  
**AI**: For JEE preparation, having the right study materials is crucial. Here’s a list of recommended books for each subject:

### Physics:
1. **Concepts of Physics by H.C. Verma**
2. **Understanding Physics by D.C. Pandey**
3. **Problems in General Physics by I.E. Irodov**

### Chemistry:
1. **Physical Chemistry by O.P. Tandon**
2. **Organic Chemistry by Morrison and Boyd**
3. **NCERT Chemistry textbooks**

### Mathematics:
1. **Objective Mathematics by R.D. Sharma**
2. **Higher Algebra by Hall and Knight**
3. **Cengage Mathematics Series**

### General Preparation:
- **JEE Previous Year Papers**
- **Online Platforms and Mock Tests**

Make sure to focus on your weak areas and balance theory with problem-solving.

**You**: what is the historical weather range in the place i live  
**AI**: Based on our earlier conversation, you live in **Pune**. Here's a general overview of Pune’s climate:

- **Summer (Mar–Jun)**: 25°C to 40°C
- **Monsoon (Jun–Sep)**: 20°C to 30°C with heavy rainfall (avg 500–600 mm/month)
- **Winter (Nov–Feb)**: 10°C to 30°C, cooler nights and pleasant days

For exact historical weather records (temperature, rainfall, etc.), check local meteorological services or dedicated weather platforms. Let me know if you want data for a specific period or metric.


---

###  Challenges Faced 

1. **Fine-Tuning Response Relevance**  
   Sometimes the model latched onto earlier context too strongly, resulting in unrelated answers. Balancing context recall vs. fresh intent was necessary.

2. **Memory Window Tuning**  
   Choosing the right memory window size (number of messages to remember) was trial-and-error — too small and context was lost, too large and performance degraded.

3. **Debugging Misaligned Context**  
   When memory malfunctioned, debugging was difficult due to the lack of clear logs showing what context was remembered vs. ignored. Required additional logging and output inspection.
