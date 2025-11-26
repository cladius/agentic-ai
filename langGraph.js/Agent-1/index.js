import { config } from 'dotenv' // Load environment variables from .env file
config()

// Import prompt-sync for user input in terminal
import promptSync from 'prompt-sync';
const prompt = promptSync();

// Import necessary LangChain modules
import { ChatGroq } from "@langchain/groq";
import { Graph} from '@langchain/langgraph'
 
// Initialize the ChatGroq model with API key and parameters
const model = new ChatGroq({
  apiKey: process.env.GROQ_API_KEY, // API key stored in .env
  model: 'llama-3.3-70b-versatile', // Selected Groq model
  temperature: 0.1                  // Low temperature for focused responses
})

// Create a new LangGraph workflow 
const graph = new Graph()

// Add a node named "chat" that handles LLM response generation
graph.addNode('chat', async (input) => {
  // Invoke the model with the incoming user message
  const res = await model.invoke([{ role: "user", content: input }]);
  return res.content ;  // Return only the generated text
});

// Link start → chat → end in the graph
graph.addEdge("__start__", "chat");
graph.addEdge("chat" ,"__end__")

// Compile the graph for execution
const compiledGraph = graph.compile();

// Function to interact with the agent
const agentCall = async () => {
  try {

    // Prompt user for input
    let userInput = prompt("Hi user! I am you AI Assistant. Enter your query: ");
    
    // Invoke the graph with a system-style instruction + user query
    const result = await compiledGraph.invoke("You are a helpful AI assistant. Provide a detailed yet concise response to user query in about 50 - 100 words with accuracy. The user query is: " + userInput);
    console.log("Result: ", result); // Output the final model response
  } 
  catch (err) {
    // Catch and display errors from graph execution or API calls
    console.error("Error running graph: ", err);
  }
};

// Start the agent interaction
agentCall();