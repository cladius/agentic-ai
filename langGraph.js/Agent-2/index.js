import { config } from 'dotenv';
config();

import promptSync from 'prompt-sync';
const prompt = promptSync();

import { ChatGroq } from "@langchain/groq";
import { Graph } from "@langchain/langgraph";
import { BufferMemory } from "langchain/memory";
import { HumanMessage, SystemMessage } from "@langchain/core/messages";

// Initialize memory to store conversation history
const memory = new BufferMemory({
  returnMessages: true,
  memoryKey: "history" // key used to extract from memory.loadMemoryVariables()
});

// Initialize the Groq chat model
const model = new ChatGroq({
  apiKey: process.env.GROQ_API_KEY,
  model: 'meta-llama/llama-4-maverick-17b-128e-instruct',
  temperature: 0.2
});

const graph = new Graph();

// Define a "chat" node that processes conversation
graph.addNode("chat", async ({ input, history }) => {
  const messages = [ // Base system instruction for the AI
    new SystemMessage("You are a helpful AI assistant. Keep answers concise and friendly, within 50-100 words.")
  ];

  if (history && history.length > 0) {
    messages.push(...history); // pulled from BufferMemory
  }

  // Add new human message
  messages.push(new HumanMessage(input));

  const response = await model.invoke(messages);

  // Save user input + model output in memory for future context
  await memory.saveContext({ input }, { output: response.content });

  return response.content;
});

// Define graph edges
graph.addEdge("__start__", "chat");
graph.addEdge("chat", "__end__");

const compiledGraph = graph.compile();

// Function to interact with the agent
const agentCall = async () => {
  try {
    console.log("Hi user! I am your AI Assistant. Let's chat.");
    while (true) {
      const userInput = prompt("You: ");
      if (userInput.toLowerCase() === "exit") break;

      // Load chat history stored by BufferMemory
      const memoryVars = await memory.loadMemoryVariables({}); // pulls history
      // returns an object like { history: [HumanMessage, AIMessage, HumanMessage, ...] } 
      
      const result = await compiledGraph.invoke({
        input: userInput,
        history: memoryVars.history ?? []
        // Use history if available; otherwise default to an empty array
     
      });
      console.log("AI:", result, "\n");
    }
  } 
  catch (err) {
    console.error("Error running graph:", err);
  }
};

// Start the agent
agentCall();
