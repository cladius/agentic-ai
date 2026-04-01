package com.langchain4j.level4.core;

import com.langchain4j.level4.agent.Assistant;
import com.langchain4j.level4.config.LangChainConfig;
import com.langchain4j.level4.ingest.DocumentIngestor;
import com.langchain4j.level4.ingest.FileSelector;
import com.langchain4j.level4.tools.WebSearchToolProvider;
import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.memory.ChatMemory;
import dev.langchain4j.memory.chat.MessageWindowChatMemory;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.model.openai.OpenAiChatModel;
import dev.langchain4j.service.AiServices;
import dev.langchain4j.store.embedding.EmbeddingMatch;
import dev.langchain4j.store.embedding.EmbeddingSearchRequest;
import dev.langchain4j.store.embedding.weaviate.WeaviateEmbeddingStore;
import dev.langchain4j.web.search.WebSearchTool;

import java.io.File;
import java.util.List;
import java.util.Scanner;

public class DocumentService {

    private final EmbeddingModel embeddingModel = LangChainConfig.embeddingModel();
    private final WeaviateEmbeddingStore embeddingStore = LangChainConfig.embeddingStore();
    private final OpenAiChatModel chatModel = LangChainConfig.chatModel();
    private final Assistant assistant;
    private final DocumentIngestor ingestor;

    public DocumentService() {
        ingestor = new DocumentIngestor(embeddingModel, embeddingStore);

        ChatMemory memory = MessageWindowChatMemory.builder()
                .maxMessages(10)
                .build();

        WebSearchTool webTool = WebSearchToolProvider.provide();

        assistant = AiServices.builder(Assistant.class)
                .chatModel(chatModel)
                .chatMemory(memory)
                .tools(webTool)
                .build();
    }

    public void run() {
        Scanner scanner = new Scanner(System.in);
        System.out.print("Do you want to ingest new documents? (yes/no): ");
        String userChoice = scanner.nextLine().trim().toLowerCase();

        if (userChoice.equals("yes")) {
            List<File> files = FileSelector.selectPdfFiles();
            if (files.isEmpty()) {
                System.out.println("No files selected. Skipping ingestion.");
            } else {
                for (File file : files) {
                    try {
                        ingestor.ingest(file);
                        System.out.println("Ingested: " + file.getName());
                    } catch (Exception e) {
                        System.out.println("Error ingesting " + file.getName() + ": " + e.getMessage());
                    }
                }
            }
        } else {
            System.out.println("Skipping document ingestion.");
        }
        chatLoop();
    }


    private void chatLoop() {
        Scanner scanner = new Scanner(System.in);
        System.out.println("\n=== Ask questions about the documents (type 'exit' to quit) ===");

        while (true) {
            System.out.print("\nYou: ");
            String question = scanner.nextLine();
            if (question.equalsIgnoreCase("exit")) break;

            var queryEmbedding = embeddingModel.embed(question).content();
            var request = EmbeddingSearchRequest.builder()
                    .queryEmbedding(queryEmbedding)
                    .maxResults(3)
                    .build();

            List<EmbeddingMatch<TextSegment>> matches = embeddingStore.search(request).matches();

            StringBuilder context = new StringBuilder();
            for (EmbeddingMatch<TextSegment> match : matches) {
                context.append(match.embedded()).append("\n");
            }

            System.out.println("Matched Context:\n" + context);
            String response = assistant.answer(context.toString(), question);
            System.out.println("AI: " + response);
        }

        scanner.close();
    }
}
