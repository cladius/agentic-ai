package com.langchain4j.level5.ingest;

import dev.langchain4j.data.document.Document;
import dev.langchain4j.data.document.DocumentSplitter;
import dev.langchain4j.data.document.Metadata;
import dev.langchain4j.data.document.splitter.DocumentSplitters;
import dev.langchain4j.data.embedding.Embedding;
import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.store.embedding.weaviate.WeaviateEmbeddingStore;

import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class TextIngestor {

    private final EmbeddingModel embeddingModel;
    private final WeaviateEmbeddingStore embeddingStore;
    private final DocumentSplitter splitter;

    public TextIngestor(EmbeddingModel embeddingModel, WeaviateEmbeddingStore embeddingStore) {
        this.embeddingModel = embeddingModel;
        this.embeddingStore = embeddingStore;
        this.splitter = DocumentSplitters.recursive(500, 50);
    }

    public void ingestRawText(String rawText, String source) {
        Document doc = Document.from(rawText);
        List<TextSegment> segments = splitter.split(doc);

        Instant now = Instant.now();
        int chunkIndex = 0;

        for (TextSegment segment : segments) {
            try {
                Embedding embedding = embeddingModel.embed(segment.text()).content();

                Map<String, Object> meta = new HashMap<>();
                meta.put("source", source);
                meta.put("chunk_index", chunkIndex);
                meta.put("timestamp", now.toString());     

                Metadata metadata = Metadata.from(meta);
                TextSegment segmentWithMetadata = TextSegment.from(segment.text(), metadata);
                embeddingStore.add(embedding, segmentWithMetadata);
                chunkIndex++;
            } catch (dev.langchain4j.exception.InvalidRequestException e) {
                System.err.println("Embedding blocked by moderation for chunk " + chunkIndex + ": " + e.getMessage());
            }
        }

        System.out.println("Ingested text into Weaviate from : " + source);
    }

}
