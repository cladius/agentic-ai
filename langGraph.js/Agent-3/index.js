import promptSync from 'prompt-sync';
const prompt = promptSync();
import dotenv from "dotenv";
dotenv.config();

import { StateGraph } from "@langchain/langgraph";
import { ChatGroq } from "@langchain/groq";
import { TavilySearch } from "@langchain/tavily";
import { ChatMessageHistory } from "langchain/stores/message/in_memory";
import { AIMessage, HumanMessage } from "@langchain/core/messages";
import { z } from "zod";
import { ToolNode } from "@langchain/langgraph/prebuilt"; 
import { tool } from "@langchain/core/tools";

// === SCHEMA ===
// Define the schema for the graph's state
const schema = z.object({
  input: z.string(),
  finalAnswer: z.string().optional(),
  messages: z.array(z.any()).optional(), // Required for ToolNode passes tool calls/results
});

// Initialize Tavily Search with your API key
const tavilyTool = new TavilySearch({ apiKey: process.env.TAVILY_API_KEY });

// Groq LLM
const llm = new ChatGroq({
  apiKey: process.env.GROQ_API_KEY,
  model: "meta-llama/llama-4-maverick-17b-128e-instruct", 
  temperature: 0.1, // Low temperature = more deterministic answers
});

// Define a tool wrapper for Tavily Search
// This is what the LLM will call when it decides tool use is necessary
const searchTool = tool(
  async ({ query }) => {
    const toolResult = await tavilyTool.invoke({ query });
    return {
      results: toolResult?.results || [],
    };
  },
  {
    name: "search",
    description:
      "Search the web for current or real-time information, such as today's date, time, latest news, or recent events.",
    schema: z.object({
      query: z.string().describe("The search query to send to the web"),
    }),
  }
);

// Wrap tools into a ToolNode (LangGraph requirement)
const toolNode = new ToolNode([searchTool])

// LLM with tools bound
const llmWithTools = llm.bindTools([searchTool]);

// In-memory chat history
const messageHistory = new ChatMessageHistory();

// === LLM Node ===
// decides whether to: answer directly or call a tool, depending on the user's question.
async function llmNode(state) {
  const query = state.input;

  const history = await messageHistory.getMessages(); // Retrieve conversation history
  const chat = [
    {
      role: "system",
      content: `You are an assistant with access to a tool called "search" for finding real-time or current information, like today's date or live events.
Only use the tool if the user's query requires current or web-based information. For greetings or general knowledge, reply directly without calling any tool.
⚠️  If the input includes a "[Summarized answer:" section, it means the tool has already been called and the result was summarized.
Carefully read the full input, and call the tool again only and only if the summarised answer is not sufficient to answer the query. Otherwise, respond directly and do not call the tool again.`,
    },
    ...history,
    new HumanMessage(query),
  ];

  const response = await llmWithTools.invoke(chat);
  
  let messages;
  // If LLM requested a tool call (response.tool_calls exists)
  if ("tool_calls" in response && response.tool_calls?.length) {
    messages = [new AIMessage({ tool_calls: response.tool_calls, content: "" })];
  } else {
    // No tool call → Give direct answer
    const finalAnswer = response.content || "Sorry, I didn't understand.";

    // Save this turn in memory
    await messageHistory.addMessage(new HumanMessage(query));
    await messageHistory.addMessage(new AIMessage(finalAnswer));
    return { finalAnswer };
  }

  // Save tool call request into memory
  await messageHistory.addMessage(new HumanMessage(query));
  await messageHistory.addMessage(messages[0]);
  
  return {
    messages,
    input: state.input, 
  };
}

// === Summarization Node ===
// This node receives the raw output from the tool and summarizes it
async function summarizeNode(state) {
  const toolMessage = state.messages[state.messages.length - 1];
  let toolResult = toolMessage?.tool_call_result;

  // Some tool responses may come as JSON strings → parse them
  if (!toolResult && typeof toolMessage?.content === "string") {
  try {
    toolResult = JSON.parse(toolMessage.content);
  } catch (err) {
    console.error("Failed to parse tool content as JSON:", toolMessage.content);
  }
}

  // Extract top 3 results for summarization
  const combinedText = toolResult.results
    ?.slice(0, 3)
    .map((r) => r.content)
    .filter(Boolean)
    .join("\n\n");

  if (!combinedText) {
    return { finalAnswer: "Sorry, I couldn't find relevant information." };
  }

  // Summarize the extracted text using the LLM
  const summaryPrompt = [
    {
      role: "system",
      content:
        "Summarize the following information clearly and concisely for the user. Don't list sources or include links.",
    },
    {
      role: "user",
      content: combinedText,
    },
  ];

  const summaryResponse = await llm.invoke(summaryPrompt);

  const finalAnswer = summaryResponse?.content || "Sorry, I couldn't generate a summary.";
  
  await messageHistory.addMessage(new AIMessage(finalAnswer));

  return {finalAnswer,
    input: `${state.input}\n[Summarized answer: ${finalAnswer}]`, };
}

// === Router Logic ===
// Decides which node to route to after LLM execution
function routerFromLLM(state) {

  // If tool call exists → go to "tool" node
  if (state.messages?.[0]?.tool_calls?.length) return "tool";
  
  return "__end__"; // // Otherwise → finish execution
}

// === Build Graph ===
const graph = new StateGraph(schema);
const compiledGraph = graph
  .addNode("llm", llmNode)
  .addNode("tool", toolNode)
  .addNode("summarize", summarizeNode)
  .addEdge("__start__", "llm")
  .addConditionalEdges("llm", routerFromLLM)
  .addEdge("tool", "summarize")
  .addEdge("summarize", "llm")
  .compile();

// === CHAT LOOP ===
const agentCall = async () => {
  try {
    console.log("Hi user! I am your AI Assistant. Let's chat.");
    while (true) {
      const userinput = prompt("You: ");
      if (userinput.toLowerCase() === "exit") break;
      const result = await compiledGraph.invoke({ input: userinput });
      console.log("Agent:", result.finalAnswer, "\n");
    }
  } catch (err) {
    console.error("Error running graph:", err);
  }
};

agentCall();
