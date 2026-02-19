package com.langchain4j.level5.core;

import com.langchain4j.level5.agents.Assistant;
import com.langchain4j.level5.config.LangChainConfig;
import com.langchain4j.level5.ingest.TextIngestor;
import com.langchain4j.level5.tools.*;
import com.langchain4j.level5.tools.PodcastTool;

import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.memory.ChatMemory;
import dev.langchain4j.memory.chat.MessageWindowChatMemory;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.model.openai.OpenAiChatModel;
import dev.langchain4j.service.AiServices;
import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.store.embedding.EmbeddingMatch;
import dev.langchain4j.store.embedding.EmbeddingSearchRequest;
import dev.langchain4j.store.embedding.weaviate.WeaviateEmbeddingStore;
import dev.langchain4j.web.search.WebSearchTool;


import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Scanner;
import java.util.concurrent.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;


public class QAService {

    private final EmbeddingModel embeddingModel;
    private final WeaviateEmbeddingStore embeddingStore;
    private final Assistant assistant;
    private final DocumentService documentService;
    private final YoutubeService youtubeService;
    private final TextIngestor textIngestor;
    private final ChatMemory chatMemory;
    private final QueryTransformer queryTransformer;
    private final ExecutorService executorService;
    private final ScraperService scraperService;
    private final PodcastService podcastService;
    private final MindmapService mindmapService;
    private static final Pattern URL_PATTERN = Pattern.compile("\\bhttps?://[^\\s<>\"']+\\b", Pattern.CASE_INSENSITIVE);
    private static final double MERGE_MARGIN = 0.10;

    public QAService() throws IOException {
        this.embeddingModel = LangChainConfig.embeddingModel();
        this.embeddingStore = LangChainConfig.embeddingStore();
        this.documentService = new DocumentService();
        this.youtubeService = new YoutubeService();
        this.textIngestor = new TextIngestor(embeddingModel, embeddingStore);
        this.scraperService = new ScraperService();
        this.podcastService = new PodcastService();
        this.mindmapService = new MindmapService();

        this.chatMemory = MessageWindowChatMemory.builder().maxMessages(15).build();

        WebSearchTool webTool = WebSearchToolProvider.provide();

        OpenAiChatModel chatModel = LangChainConfig.chatModel();

        this.assistant = AiServices.builder(Assistant.class)
                .chatModel(chatModel)
                .chatMemory(this.chatMemory)
                .tools(
                        webTool,
                        new PodcastTool(this.podcastService),
                        new MindMapTool(this.mindmapService)
                )
                .build();

        this.queryTransformer = AiServices.builder(QueryTransformer.class)
                .chatModel(chatModel)
                .chatMemory(this.chatMemory)
                .build();

        this.executorService = Executors.newFixedThreadPool(Math.max(2, Runtime.getRuntime().availableProcessors()));
    }

    public void startChatLoop() throws IOException, InterruptedException {
        Scanner scanner = new Scanner(System.in);
        System.out.println("\n=== Type 1 to ingest documents, or just chat/paste links in your messages ===");

        while (true) {
            System.out.print("\nYou: ");
            String input = scanner.nextLine().trim();
            if (input.equalsIgnoreCase("exit")) break;

            // Doc
            if (input.equals("1")) {
                documentService.ingestDocuments();
                System.out.println("Documents ingested.");
                continue;
            }

            List<String> urls = extractUrls(input);
            String userTextOnly = input.replaceAll(URL_PATTERN.pattern(), "").trim();

            List<Future<String>> ingestionFutures = new ArrayList<>();
            if (!urls.isEmpty()) {
                for (String url : urls) {
                    ingestionFutures.add(executorService.submit(() -> ingestAndPersistUrl(url)));
                }
            }

            StringBuilder immediateContext = new StringBuilder();
            if (!userTextOnly.isEmpty()) {
                immediateContext.append(userTextOnly).append("\n");
            }

            for (Future<String> f : ingestionFutures) {
                try {
                    String content = f.get(); // Blocks until the task is fully done
                    if (content != null && !content.isBlank()) {
                        immediateContext.append(content).append("\n");
                    }
                } catch (ExecutionException ee) {
                    System.err.println("Ingestion task failed: " + ee.getMessage());
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                }
            }


            String transformedQuery = null;
            try {
                transformedQuery = queryTransformer.transform(input);
            } catch (Exception e) {
                transformedQuery = input;
                System.err.println("Query transformer failed; using raw input. " + e.getMessage());
            }

            String retrievedContext = retrieveFromDB(transformedQuery);
            String finalContext = decideContextToUse(transformedQuery, immediateContext.toString(), retrievedContext);
            String response = assistant.answer(finalContext, input);
            System.out.println("AI: " + response);
        }
    }

    private String ingestAndPersistUrl(String url) {
        try {
            String content = null;
            if (isYouTubeUrl(url)) {
                YoutubeService.IngestResult yt = youtubeService.ingest(url);
                if (yt != null && yt.transcript != null && !yt.transcript.isBlank()) {
                    content = yt.transcript;
                }
            } else {
                content = scraperService.scrape(url);
            }
            if (content != null && !content.isBlank()) {

                try {
                    textIngestor.ingestRawText(content, url);
                    System.out.println("Persisted content from: " + url);
                } catch (Exception e) {
                    System.err.println("Failed to persist content for " + url + ": " + e.getMessage());
                }
                return content;
            } else {
                System.err.println("No consumable content from: " + url);
                return null;
            }
        } catch (Exception e) {
            System.err.println("Error ingesting " + url + " : " + e.getMessage());
            return null;
        }
    }

    private String retrieveFromDB(String transformedQuery) {
        try {
            var queryEmbedding = embeddingModel.embed(transformedQuery).content();
            var request = EmbeddingSearchRequest.builder()
                    .queryEmbedding(queryEmbedding)
                    .maxResults(5)
                    .build();

            List<EmbeddingMatch<TextSegment>> matches = embeddingStore.search(request).matches();
            StringBuilder builder = new StringBuilder();
            for (EmbeddingMatch<TextSegment> m : matches) {
                if (m.embedded() != null && m.embedded().text() != null) {
                    builder.append(m.embedded().text()).append("\n");
                }
            }
            return builder.toString();
        } catch (Exception e) {
            System.err.println("Vector store retrieval failed: " + e.getMessage());
            return "";
        }
    }

    private String decideContextToUse(String transformedQuery, String immediateContext, String retrievedContext) {
        return retrievedContext;
//        System.out.println("Immediate:"+immediateContext);
//        System.out.println("Retreived"+retrievedContext);
//        boolean hasImmediate = immediateContext != null && !immediateContext.isBlank();
//        boolean hasRetrieved = retrievedContext != null && !retrievedContext.isBlank();

//        if (!hasImmediate && !hasRetrieved) {
//            return "";
//        }
//        if (!hasImmediate) return retrievedContext;
//        if (!hasRetrieved) return immediateContext;
//
//        try {
//            float[] qEmb = embeddingModel.embed(transformedQuery).content().vector();
//            float[] immEmb = embeddingModel.embed(immediateContext).content().vector();
//            float[] retEmb = embeddingModel.embed(retrievedContext).content().vector();
//
//            double immScore = cosineSimilarity(qEmb, immEmb);
//            double retScore = cosineSimilarity(qEmb, retEmb);
//
            // Decision
//            if (immScore >= retScore + MERGE_MARGIN) {
//                System.out.println("INFO: Using immediate (new) context only (higher relevance).");
//                return immediateContext;
//            } else if (retScore >= immScore + MERGE_MARGIN) {
//                System.out.println("INFO: Using retrieved (historical) context only (higher relevance).");
//                return retrievedContext;
//            } else {
//                System.out.println("INFO: Merging immediate and retrieved context (both relevant).");
//                return immediateContext + "\n" + retrievedContext;
//            }
//        } catch (Exception e) {
//
//            System.err.println("Context decision failed; defaulting to merge. " + e.getMessage());
//            return immediateContext + "\n" + retrievedContext;
//        }
    }

    private double cosineSimilarity(float[] a, float[] b) {
        double dot = 0.0;
        double normA = 0.0;
        double normB = 0.0;

        for (int i = 0; i < a.length; i++) {
            dot += a[i] * b[i];
            normA += a[i] * a[i];
            normB += b[i] * b[i];
        }

        return dot / (Math.sqrt(normA) * Math.sqrt(normB));
    }

    private List<String> extractUrls(String text) {
        List<String> urls = new ArrayList<>();
        Matcher matcher = URL_PATTERN.matcher(text);
        while (matcher.find()) {
            urls.add(matcher.group());
        }
        return urls;
    }

    private boolean isYouTubeUrl(String url) {
        if (url == null) return false;
        return url.matches("^(https?://)?(www\\.)?(youtube\\.com|youtu\\.be)/.+$");
    }

    public void shutdown() {
        executorService.shutdown();
        try {
            if (!executorService.awaitTermination(2, TimeUnit.SECONDS)) {
                executorService.shutdownNow();
            }
        } catch (InterruptedException e) {
            executorService.shutdownNow();
            Thread.currentThread().interrupt();
        }
    }

    interface QueryTransformer {
        @SystemMessage("You are a query writer. Your task is to rephrase the user's query to be a standalone question, using the chat history for context if necessary.")
        String transform(String query);
    }
}
