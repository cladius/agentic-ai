package com.langchain4j.level5.tools;

import dev.langchain4j.web.search.WebSearchTool;
import dev.langchain4j.web.search.searchapi.SearchApiWebSearchEngine;

import java.util.HashMap;
import java.util.Map;

public class WebSearchToolProvider {

    public static WebSearchTool provide() {
        String apiKey = System.getenv("SEARCHAPI_KEY");
        if (apiKey == null) {
            System.out.println("SEARCHAPI_KEY not set.");
        }

        Map<String, Object> options = new HashMap<>();
        options.put("gl", "us");
        options.put("hl", "en");
        options.put("google_domain", "google.com");

        SearchApiWebSearchEngine engine = SearchApiWebSearchEngine.builder()
                .apiKey(apiKey)
                .engine("google")
                .optionalParameters(options)
                .build();

        return WebSearchTool.from(engine);
    }
}
