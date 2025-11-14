import { Graph } from "@langchain/langgraph";  
import { ChatGroq } from "@langchain/groq";
import { Chroma } from "@langchain/community/vectorstores/chroma";
import { HuggingFaceTransformersEmbeddings } from "@langchain/community/embeddings/huggingface_transformers";
import { ChatMessageHistory } from "langchain/stores/message/in_memory";
import { SystemMessage } from "@langchain/core/messages";
import Tesseract from "tesseract.js"; // OCR
import { Document } from "@langchain/core/documents";
import { RecursiveCharacterTextSplitter } from "langchain/text_splitter";
import { RunnableSequence } from "@langchain/core/runnables";
import { StringOutputParser } from "@langchain/core/output_parsers";
import promptSync from "prompt-sync";
const prompt = promptSync();
import dotenv from "dotenv";
dotenv.config();
import { EventEmitter } from "events";     
EventEmitter.defaultMaxListeners = 20; 

const llm = new ChatGroq({ 
    apiKey: process.env.GROQ_API_KEY,
    model: 'meta-llama/llama-4-maverick-17b-128e-instruct',
    temperature: 0 
});

const embeddings = new HuggingFaceTransformersEmbeddings({
    modelName: "sentence-transformers/all-MiniLM-L6-v2",
});

// -------- INITIAL STATE ----------
const initialState ={
    filePath: null,
    userId: null,
    text: null,
    vectorStore: null,
    chat_history: null,
};

async function OCRNode(state) {
    const { filePath } = state;
    let text = '';    
    try {
          const results = await Tesseract.recognize(
              filePath, // Path to the image file or a URL
              'eng',     // Language code (e.g., 'eng' for English)
          );
          text = results.data.text;
        } catch (error) {
            console.error("Error during OCR:", error);
        }
    return {...state, text };
}

async function VectorizeNode(state) {
    const { text, userId } = state;
    const collectionName = `resume_${userId}`;
    
    // Split text into chunks using LangChain splitter
    const splitter = new RecursiveCharacterTextSplitter({
    chunkSize: 500,   // Max size of each chunk
    chunkOverlap: 50 // Overlap between chunks 
    });
    
    const docs = await splitter.splitDocuments([
    new Document({ pageContent: text, metadata: { userId, source: "resume" } })
    ]);

    docs.forEach((doc, i) => {
      doc.metadata.id = `resume_doc_user123_part_${i}`;   // Attach ID inside metadata or a separate map (Chroma handles metadata)
    });

    // Creates a new Chroma instance from an existing collection in the Chroma database.
    const vectorStore = await Chroma.fromExistingCollection(embeddings, {
      collectionName, 
    });
    const count = await vectorStore.collection.count();
    if (count === 0) {
      await vectorStore.addDocuments(docs); // store using addDocuments() if collection is empty
    }
    
    console.log(`Vector store created for user: ${userId}`);
    return {...state , vectorStore : vectorStore};
}
      
async function QANode(state) {
    const {vectorStore} = state;
    let {chat_history} = state;

    chat_history = new ChatMessageHistory();
    await chat_history.addMessage(new SystemMessage("You are an AI assistant helping users extract information from resumes."));
    // here we assume the llm to be asked only resume related questions

    const retrievalChain = RunnableSequence.from([
      {
        context: async (input) => {
          const queryVec = await embeddings.embedQuery(input.question);
          const results = await vectorStore.similaritySearchVectorWithScore([queryVec], 2);
          const context = results?.[0]?.[0]?.pageContent + "\n" + results?.[1]?.[0]?.pageContent;
          return context || "No relevant context found.";
        },
        question: (input) => input.question,
      },
      async ({ context, question }) =>
        ` Answer the question based on the following context and chat history:\n\n${context}\n\nChat history: ${chat_history.messages.map(m => `${m.role}: ${m.content}`).join('\n')}\n\nQuestion: ${question}\nAnswer:`,
      llm,
      new StringOutputParser(),
    ]);
    
    while (true) {
      console.log("\n");
      const question = prompt("Ask a question (or 'exit'): ");
      if (question.toLowerCase() === "exit") break;
      
      const result = await retrievalChain.invoke({question});
      
      await chat_history.addUserMessage(question);
      await chat_history.addAIMessage(result);

      console.log("Answer:", result);
    }

    return {...state ,  chat_history: chat_history }; 
}

const graph = new Graph(initialState)
    .addNode("OCRNode", OCRNode)
    .addNode("VectorizeNode", VectorizeNode)
    .addNode("QANode", QANode)
    .addEdge("__start__", "OCRNode")
    .addEdge("OCRNode", "VectorizeNode")
    .addEdge("VectorizeNode", "QANode")
    .addEdge("QANode", "__end__")
    .compile();

async function main() {
    const filePath = prompt("Enter resume file path: ");
    const userId = "user123";

    await graph.invoke({
      filePath,
      userId
    });
}

main();
