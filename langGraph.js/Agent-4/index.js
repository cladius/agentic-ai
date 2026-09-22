import { Graph } from "@langchain/langgraph";  
import { ChatGroq } from "@langchain/groq";

import { Chroma } from "@langchain/community/vectorstores/chroma";
import { HuggingFaceTransformersEmbeddings } from "@langchain/community/embeddings/huggingface_transformers";

import { ChatMessageHistory } from "langchain/stores/message/in_memory";
import { SystemMessage } from "@langchain/core/messages";

import Tesseract from "tesseract.js"; // OCR library for extracting text from images

import { Document } from "@langchain/core/documents";
import { RecursiveCharacterTextSplitter } from "langchain/text_splitter";

import { RunnableSequence } from "@langchain/core/runnables";
import { StringOutputParser } from "@langchain/core/output_parsers";

import promptSync from "prompt-sync";
const prompt = promptSync();

import dotenv from "dotenv";
dotenv.config();

import { EventEmitter } from "events";     // Prevent event emitter warnings 
EventEmitter.defaultMaxListeners = 20; 

const llm = new ChatGroq({ 
    apiKey: process.env.GROQ_API_KEY,
    model: 'meta-llama/llama-4-maverick-17b-128e-instruct',
    temperature: 0 
});

// Embedding model used for vector store
const embeddings = new HuggingFaceTransformersEmbeddings({
    modelName: "sentence-transformers/all-MiniLM-L6-v2",
});

// -------- INITIAL STATE ----------
const initialState ={
    filePath: null,
    userId: null,
    text: null,
    vectorStore: null,
    chatHistory: null,
};

// -------------------- OCR NODE --------------------
// Extracts text content from an image using Tesseract OCR.
async function OCRNode(state) {
    const { filePath } = state;
    let text = '';    
    try {
          const results = await Tesseract.recognize(
              filePath, // Path to the image file 
              'eng',     // Language code (e.g., 'eng' for English)
          );
          text = results.data.text;
        } catch (error) {
            console.error("Error during OCR:", error);
        }
    return {...state, text };
}

// -------------------- VECTORIZATION NODE --------------------
// Splits extracted text into chunks, embeds them, and stores them in a Chroma vector store.
async function VectorizeNode(state) {
    const { text, userId } = state;
    const collectionName = `docs_${userId}`;
    
    // Split text into overlapping chunks for better retrieval accuracy
    const splitter = new RecursiveCharacterTextSplitter({
    chunkSize: 500,   // Max size of each chunk
    chunkOverlap: 50 // Overlap between chunks 
    });
    /* RecursiveCharacterTextSplitter : 
    The splitter uses a list of separators (e.g., ["\n\n", "\n", " ", ""]) and attempts to split the text using the first separator in the list.
    If a resulting chunk is smaller than the specified chunkSize, it's considered a valid chunk.
    If a chunk is larger than chunkSize, the splitter recursively applies the next separator in the list to that chunk, trying to break it down further until all chunks are within the size limit.
    */
    
    const docs = await splitter.splitDocuments([
    new Document({ pageContent: text, metadata: { userId, source: "docs" } })
    ]);

    // Add unique id metadata for each chunk
    docs.forEach((doc, i) => {
      doc.metadata.id = `doc_user123_part_${i}`;   // Attach ID inside metadata or a separate map (Chroma handles metadata)
    });

    // Creates a new Chroma instance from an existing collection in the Chroma database.
    const vectorStore = await Chroma.fromExistingCollection(embeddings, {
      collectionName, 
    });
    // Add documents only if collection is empty
    const count = await vectorStore.collection.count();
    if (count === 0) {
      await vectorStore.addDocuments(docs); 
    }
    
    console.log(`Vector store created for user: ${userId}`);
    return {...state , vectorStore : vectorStore};
}
      
// -------------------- QA(Question - Answer) NODE --------------------
// Handles user questions by retrieving relevant context from the vector store and generating answers using the LLM.
async function QANode(state) {
    const {vectorStore} = state;
    let {chatHistory} = state;

    chatHistory = new ChatMessageHistory();
    await chatHistory.addMessage(new SystemMessage("You are an AI assistant helping users extract information from documents."));

    // Retrieval + LLM pipeline
    const retrievalChain = RunnableSequence.from([
      {
        // Look up semantic context from vector store
        context: async (input) => {

          // Convert the user's natural-language question into an embedding vector
          const queryVec = await embeddings.embedQuery(input.question);
          // Perform a similarity search in the vector store using the query embedding and returning the top 2 most relevant chunks
          const results = await vectorStore.similaritySearchVectorWithScore([queryVec], 2);
          // Extract the text content from the retrieved documents.
          const context = results?.[0]?.[0]?.pageContent + "\n" + results?.[1]?.[0]?.pageContent;
          return context || "No relevant context found.";
        },
        question: (input) => input.question,
      },

      // Format prompt for the LLM
      async ({ context, question }) =>
        ` Answer the question based on the following context and chat history:\n\n${context}\n\nChat history: ${chatHistory.messages.map(m => `${m.role}: ${m.content}`).join('\n')}\n\nQuestion: ${question}\nAnswer:`,
      llm,
      new StringOutputParser(),
    ]);
    
    // Interactive QA loop
    while (true) {
      console.log("\n");
      const question = prompt("Ask a question (or 'exit'): ");
      if (question.toLowerCase() === "exit") break;
      
      const result = await retrievalChain.invoke({question});
      
      await chatHistory.addUserMessage(question);
      await chatHistory.addAIMessage(result);

      console.log("Answer:", result);
    }

    return {...state ,  chatHistory: chatHistory }; 
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
    const filePath = prompt("Enter file path: ");
    const userId = "user123";

    await graph.invoke({
      filePath,
      userId
    });
}

main();
