import promptSync from 'prompt-sync';
const prompt = promptSync();
import dotenv from "dotenv";
dotenv.config();

import { createTools } from "./tools/processing_tools.js";
import { createIngestionTools } from "./tools/ingestion_tools.js";

import { StateGraph, END } from "@langchain/langgraph";
import { ChatGroq } from "@langchain/groq";
import { AIMessage, HumanMessage, SystemMessage, ToolMessage } from "@langchain/core/messages";
import { ToolNode } from "@langchain/langgraph/prebuilt";

import { Chroma } from "@langchain/community/vectorstores/chroma";
import { HuggingFaceTransformersEmbeddings } from "@langchain/community/embeddings/huggingface_transformers";
import { Document } from "@langchain/core/documents";
import { RecursiveCharacterTextSplitter } from "langchain/text_splitter";

import fs from "fs";

// =================================================================
// 1. STATE DEFINITION
// =================================================================
const agentState = {             //Represents the state of our agent.
  last_input: {                  // The most recent user input.                
    value: (x, y) => y,
    default: () => "",
  },
  messages: {                   // The history of the conversation. 
    value: (x, y) => x.concat(y),
    default: () => [],
  },
  route_decision: {            // Decision from the planner node to route the graph.
    value: (x, y) => y, 
    default: () => "",
  },
  vectorStore: {
      value: (x, y) => y, // Always replace with the latest instance
      default: () => null,
  },
  userId: {             // The user ID for the current conversation thread.
      value: (x, y) => y,
      default: () => "",
  }
};

// =================================================================
// 2. LLM and TOOLS INITIALIZATION
// =================================================================

const llm = new ChatGroq({
  apiKey: process.env.GROQ_API_KEY,
  model: "meta-llama/llama-4-maverick-17b-128e-instruct",
  temperature: 0,
});

// ✨ Initialize embeddings model
const embeddings = new HuggingFaceTransformersEmbeddings({
    modelName: "sentence-transformers/all-MiniLM-L6-v2",
});

// --- INGESTION TOOLS ---
const ingestionTools = createIngestionTools();
const llmWithIngestionTools = llm.bindTools(ingestionTools);

// --- PROCESSING TOOLS ---
const processingTools = createTools(llm); 
const processingToolNode = new ToolNode(processingTools);
const llmWithProcessingTools = llm.bindTools(processingTools);

// =================================================================
// 3. AGENT NODES
// =================================================================

// The central hub. Classifies the user's input to decide where to go next.
const planner_node = async (state) => {
  const { last_input } = state;
  const systemPrompt = `You are a classifier. Your only job is to determine if the user's input is a resource, a query, or an exit command.
  - A 'resource' is a URL (http, https), a local file path (e.g., C:/, /users/), or raw text meant to be used as context.
  - A 'query' is a question or a command asking to perform an action (e.g., 'summarize', 'what is?', 'make notes', 'create a mind map', 'create a podcast').
  - 'exit' means the user wants to end the conversation.
  Respond with ONLY 'resource', 'query', or 'exit'.`;
  
  const response = await llm.invoke([new SystemMessage(systemPrompt), new HumanMessage(last_input)]);
  
  return { route_decision: response.content };
};

// Handles resource ingestion. It uses an LLM with ingestion tools to process URLs, PDFs and text.
const ingestion_node = async (state) => {
  const { last_input } = state;
  const systemPrompt = "You are an expert at identifying all resources (URLs, file paths, raw text) in a user's input. For each identified resource, call the appropriate ingestion tool.";
  
  const response = await llmWithIngestionTools.invoke([new SystemMessage(systemPrompt), new HumanMessage(last_input)]);
  
  // The response will contain tool calls that the next node will execute.
  return { messages: [response] };
};

// Processes tool calls from ingestion_node ,splits & stores text into Chroma vector DB
const ingestion_tool_node = async (state) => {
  const { messages, userId } = state;
  const lastMessage = messages[messages.length - 1];
  
  // This is the list of tool calls the LLM wants to make
  const toolCalls = lastMessage.tool_calls;
  
  // Create a map of our tools for easy access
  const toolMap = new Map(ingestionTools.map(tool => [tool.name, tool]));
  const toolOutputs = [];
  const toolMessages = [];
  
  // Loop through each tool call and invoke it directly
  for (const call of toolCalls) {
    const toolToCall = toolMap.get(call.name);
    if (toolToCall) {
      const output = await toolToCall.invoke(call.args);
      toolOutputs.push(output);
      toolMessages.push(new ToolMessage({ tool_call_id: call.id, content: `Successfully processed ${call.args}` }));
    }
  }
  // Aggregate all the text extracted by the tools
  const newContent = toolOutputs.join("\n\n");
  
  // --- Vectorization Step ---
  const splitter = new RecursiveCharacterTextSplitter({ chunkSize: 500, chunkOverlap: 50 });
  const docs = await splitter.splitDocuments([
    new Document({ pageContent: newContent, metadata: { userId, source: "user_upload" } })
  ]);
  
  const collectionName = `agent_docs_${userId}`;
  const vectorStore = new Chroma(embeddings, { collectionName });
  
  await vectorStore.addDocuments(docs);
  console.log(`✅ Content chunked and added to the vector store for user: ${userId}`);
  
  const confirmationMessage = new AIMessage("✅ Content has been processed and stored. What would you like to do with it?");

  return {
    messages: [...toolMessages, confirmationMessage],
    vectorStore: vectorStore, // Pass the vector store instance back to the state
  };
};

// Handles user queries. It can answer from context, from general knowledge, or use processing tools. 
// It will first try to retrieve relevant documents from the vector store based on the user's query.
const responseQuery_node = async (state) => {
  const { last_input, messages, vectorStore } = state; 
  
  let retrieved_context = "No relevant context found.";
  const lastMessage = messages.length > 0 ? messages[messages.length - 1] : null;

  if (vectorStore) {
      if (!lastMessage || lastMessage._getType() !== "tool") {
        console.log("✅ Retrieving relevant context from vector store...");
      }
      const queryVector = await embeddings.embedQuery(last_input);
      const results = await vectorStore.similaritySearchVectorWithScore([queryVector], 2);
      retrieved_context = results.map(result => result[0].pageContent).join("\n\n");
  }

  const systemPrompt = `You are a helpful and expert AI assistant. You MUST answer the user's query based ONLY on the provided context below.
    Context:
    ---
    ${retrieved_context}
    ---
    If the context is not sufficient, you may use a tool. Your reasoning process:
    1.  Analyze the user's query.
    2.  If the context provides enough information, formulate a final answer.
    3.  If not, you may call a tool (Summarization, NoteTaking, etc.) using the retrieved context to process it further.
    4.  After a tool runs, evaluate its output to form a final answer.
    IMPORTANT: Once you have a satisfactory answer, respond directly to the user without tool calls.`;

  const conversation = [new SystemMessage(systemPrompt), ...messages, new HumanMessage(last_input)];
  const response = await llmWithProcessingTools.invoke(conversation);
  
  return { messages: [new HumanMessage(last_input), response] };
};

// =================================================================
// 4. GRAPH ROUTING AND CONSTRUCTION
// =================================================================
const route_planner = (state) => {
  const { route_decision } = state;
  if (route_decision.includes("resource")) return "ingestion_node";
  if (route_decision.includes("query")) return "responseQuery_node";
  return END;
};

const route_after_query = (state) => {
  const { messages } = state;
  const lastMessage = messages[messages.length - 1];
  // If the last message contains tool calls, route to the processing tool node.
  if (lastMessage.tool_calls?.length) {
    return "processing_tool_node";
  }
  // If the last message is a final answer (no tool calls), end the conversation.
  return END ;
};
const workflow = new StateGraph({ channels: agentState });

workflow.addNode("planner_node", planner_node);
workflow.addNode("ingestion_node", ingestion_node);
workflow.addNode("ingestion_tool_node", ingestion_tool_node);
workflow.addNode("responseQuery_node", responseQuery_node);
workflow.addNode("processing_tool_node", processingToolNode);

workflow.addEdge("__start__", "planner_node");
workflow.addConditionalEdges(
  "planner_node", 
  route_planner,
  {
    "ingestion_node": "ingestion_node",
    "responseQuery_node": "responseQuery_node",
    "__end__": END
  }
);

// Ingestion Spoke
workflow.addEdge("ingestion_node", "ingestion_tool_node");
workflow.addEdge("ingestion_tool_node", END); 

// Query Spoke
workflow.addConditionalEdges(
  "responseQuery_node",
  route_after_query,
  {
    "processing_tool_node": "processing_tool_node",
    "__end__" : END // End if final answer
  }
);
workflow.addEdge("processing_tool_node", "responseQuery_node"); // Loop back to process tool results
const app = workflow.compile();

// =================================================================
// 6. GRAPH VISUALIZATION EXPORT FUNCTION
// =================================================================

async function exportGraphImage(compiledGraph, fileName = "graph.png") {
  try {
    const drawableGraph = await compiledGraph.getGraphAsync();
    const image = await drawableGraph.drawMermaidPng();

    if (Buffer.isBuffer(image)) {
      fs.writeFileSync(fileName, image);
    } else if (typeof image.arrayBuffer === "function") {
      const buffer = Buffer.from(await image.arrayBuffer());
      fs.writeFileSync(fileName, buffer);
    }

    console.log(`✅ Graph structure exported successfully as ${fileName}`);
  } catch (error) {
    console.error("❌ Error generating graph visualization:", error);
  }
}

await exportGraphImage(app, "./assets/agent_graph.png");

// =================================================================
// 7. AGENT EXECUTION LOOP
// =================================================================

const agent_Call = async () => {
  console.log("🤖 Hello! I am your AI assistant. You can provide a resource (URL, PDF, text) or ask a query.");
  
  // This Map will act as our in-memory storage for all conversation states.
  const conversationStates = new Map();

  while (true) {
    // Ask for a User ID to simulate different users or conversation threads.
    const userId = prompt("Enter a User ID to start or continue a conversation (e.g., 'user_1'): ");
    if (userId.toLowerCase() === "exit") {
      console.log("🤖 Goodbye!");
      break;
    }

    console.log(`--- Starting/Resuming Conversation with ${userId} ---`);
    
    // Inner loop for the active conversation thread.
    while (true) {
      const userinput = prompt(`${userId}: `);
      if (userinput.toLowerCase() === "exit") {
        console.log(`--- Pausing conversation with ${userId} ---`);
        break; // Exit inner loop to switch users
      }
      
      // 1. Get the state for the current thread, or create a new one if it's the first time.
      const currentState = conversationStates.get(userId) || {
        messages: [],
        userId: userId, // Pass the userId into the state
      };

      // 2. Invoke the graph with the current thread's state.
      const result = await app.invoke({ ...currentState, last_input: userinput });
      
      // 3. Save the updated state back to our map.
      conversationStates.set(userId, result);
      
      const lastAiMessage = result.messages.slice().reverse().find(
        (msg) => msg._getType() === "ai" && msg.content
      );

      if (lastAiMessage) {
        console.log("🤖 Assistant:", lastAiMessage.content);
      }
    }
  }
};

agent_Call();