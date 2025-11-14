import { config } from 'dotenv'
config()

import promptSync from 'prompt-sync';
const prompt = promptSync();

import { ChatGroq } from "@langchain/groq";
import { Graph} from '@langchain/langgraph'
 
const model = new ChatGroq({
  apiKey: process.env.GROQ_API_KEY,
  model: 'llama-3.3-70b-versatile',
  temperature: 0.1
})

const graph = new Graph()
graph.addNode('chat', async (input) => {
  const res = await model.invoke([{ role: "user", content: input }]);
  return res.content ; 
});

graph.addEdge("__start__", "chat");
graph.addEdge("chat" ,"__end__")

const compiledGraph = graph.compile();

const agent_Call = async () => {
  try {
    let userinput = prompt("Hi user! I am you AI Assistant. Enter your query: ");
    const result = await compiledGraph.invoke("You are a helpful AI assistant. Provide a detailed yet concise response to user query in about 50 - 100 words with accuracy. The user query is: " + userinput);
    console.log("Result: ", result);
  } catch (err) {
    console.error("Error running graph: ", err);
  }
};

agent_Call();