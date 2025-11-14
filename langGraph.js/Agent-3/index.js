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
const schema = z.object({
  input: z.string(),
  finalAnswer: z.string().optional(),
  messages: z.array(z.any()).optional(), // Required for ToolNode
});

const tavilyTool = new TavilySearch({ apiKey: process.env.TAVILY_API_KEY });

// Groq LLM
const llm = new ChatGroq({
  apiKey: process.env.GROQ_API_KEY,
  model: "meta-llama/llama-4-maverick-17b-128e-instruct", 
  temperature: 0.1,
});

// Tool
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

const tool_node = new ToolNode([searchTool])

const llmWithTools = llm.bindTools([searchTool]);

// In-memory session history
const messageHistory = new ChatMessageHistory();

// === LLM Node ===
async function llmNode(state) {
  const query = state.input;

  const history = await messageHistory.getMessages();
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
  if ("tool_calls" in response && response.tool_calls?.length) {
    messages = [new AIMessage({ tool_calls: response.tool_calls, content: "" })];
  } else {
    const finalAnswer = response.content || "Sorry, I didn't understand.";
    await messageHistory.addMessage(new HumanMessage(query));
    await messageHistory.addMessage(new AIMessage(finalAnswer));
    return { finalAnswer };
  }

  await messageHistory.addMessage(new HumanMessage(query));
  await messageHistory.addMessage(messages[0]);
  
  return {
    messages,
    input: state.input, 
  };
}

async function summarizeNode(state) {
  const toolMessage = state.messages[state.messages.length - 1];
  let toolResult = toolMessage?.tool_call_result;

  if (!toolResult && typeof toolMessage?.content === "string") {
  try {
    toolResult = JSON.parse(toolMessage.content);
  } catch (err) {
    console.error("Failed to parse tool content as JSON:", toolMessage.content);
  }
}

  const combinedText = toolResult.results
    ?.slice(0, 3)
    .map((r) => r.content)
    .filter(Boolean)
    .join("\n\n");

  if (!combinedText) {
    return { finalAnswer: "Sorry, I couldn't find relevant information." };
  }

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

function routerFromLLM(state) {
  if (state.messages?.[0]?.tool_calls?.length) return "tool";
  return "__end__";}

// === Build Graph ===
const graph = new StateGraph(schema);
const compiledGraph = graph
  .addNode("llm", llmNode)
  .addNode("tool", tool_node)
  .addNode("summarize", summarizeNode)
  .addEdge("__start__", "llm")
  .addConditionalEdges("llm", routerFromLLM)
  .addEdge("tool", "summarize")
  .addEdge("summarize", "llm")
  .compile();

const agent_Call = async () => {
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

agent_Call();
