package com.langchain4j.level4.config;
import dev.langchain4j.model.openai.OpenAiChatModel;
import dev.langchain4j.model.openai.OpenAiEmbeddingModel;
import dev.langchain4j.store.embedding.weaviate.WeaviateEmbeddingStore;

import java.util.List;

public class LangChainConfig {

    public static OpenAiChatModel chatModel() {
        return OpenAiChatModel.builder()
                .baseUrl("http://langchain4j.dev/demo/openai/v1")
                .apiKey("demo")
                .modelName("gpt-4o-mini")
                .build();
    }

    public static OpenAiEmbeddingModel embeddingModel() {
        return OpenAiEmbeddingModel.builder()
                .baseUrl("http://langchain4j.dev/demo/openai/v1")
                .apiKey("demo")
                .modelName("text-embedding-3-small")
                .build();
    }

    public static WeaviateEmbeddingStore embeddingStore() {
        return WeaviateEmbeddingStore.builder()
                .scheme("https")
                .host( System.getenv("HOST"))
                .apiKey( System.getenv("WAPI_KEY"))
                .textFieldName("text")
                .metadataKeys(List.of("source", "chunk_index", "timestamp"))
                .objectClass("Testing")
                .build();
    }


}

