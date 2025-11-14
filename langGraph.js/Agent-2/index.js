import { config } from 'dotenv';
config();

import promptSync from 'prompt-sync';
const prompt = promptSync();

import { ChatGroq } from "@langchain/groq";
import { Graph } from "@langchain/langgraph";
import { BufferMemory } from "langchain/memory";
import { HumanMessage, SystemMessage } from "@langchain/core/messages";

const memory = new BufferMemory({
  returnMessages: true,
  memoryKey: "history" // key used to extract from memory.loadMemoryVariables()
});

const model = new ChatGroq({
  apiKey: process.env.GROQ_API_KEY,
  model: 'meta-llama/llama-4-maverick-17b-128e-instruct',
  temperature: 0.2
});

const graph = new Graph();

graph.addNode("chat", async ({ input, history }) => {
  const messages = [
    new SystemMessage("You are a helpful AI assistant. Keep answers concise and friendly, within 50-100 words.")
  ];

  if (history && history.length > 0) {
    messages.push(...history); // pulled from BufferMemory
  }

  messages.push(new HumanMessage(input));

  const response = await model.invoke(messages);

  // Save to memory
  await memory.saveContext({ input }, { output: response.content });

  return response.content;
});

graph.addEdge("__start__", "chat");
graph.addEdge("chat", "__end__");

const compiledGraph = graph.compile();

const agent_Call = async () => {
  try {
    console.log("Hi user! I am your AI Assistant. Let's chat.");
    while (true) {
      const userinput = prompt("You: ");
      if (userinput.toLowerCase() === "exit") break;

      const memoryVars = await memory.loadMemoryVariables({}); // pulls history
      // returns an object like { history: [HumanMessage, AIMessage, HumanMessage, ...] } 
      
      const result = await compiledGraph.invoke({
        input: userinput,
        history: memoryVars.history ?? []
        // If memoryVars.history is defined (not null or undefined), use it. Otherwise, fall back to an empty array []
     
      });
      console.log("AI:", result, "\n");
    }
  } 
  catch (err) {
    console.error("Error running graph:", err);
  }
};

agent_Call();
