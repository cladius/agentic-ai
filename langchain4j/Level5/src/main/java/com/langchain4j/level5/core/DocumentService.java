package com.langchain4j.level5.core;

import com.langchain4j.level5.config.LangChainConfig;
import com.langchain4j.level5.ingest.DocumentIngestor;
import com.langchain4j.level5.ingest.FileSelector;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.store.embedding.weaviate.WeaviateEmbeddingStore;

import java.io.File;
import java.util.List;

public class DocumentService {

    private final DocumentIngestor ingestor;

    public DocumentService() {
        EmbeddingModel embeddingModel = LangChainConfig.embeddingModel();
        WeaviateEmbeddingStore embeddingStore = LangChainConfig.embeddingStore();
        this.ingestor = new DocumentIngestor(embeddingModel, embeddingStore);
    }

    public void ingestDocuments() {
        List<File> files = FileSelector.selectPdfFiles();
        if (files.isEmpty()) {
            System.out.println("No files selected. Skipping ingestion.");
            return;
        }

        for (File file : files) {
            try {
                ingestor.ingest(file);
                System.out.println("Ingested: " + file.getName());
            } catch (Exception e) {
                System.out.println("Error ingesting " + file.getName() + ": " + e.getMessage());
            }
        }
    }
}
