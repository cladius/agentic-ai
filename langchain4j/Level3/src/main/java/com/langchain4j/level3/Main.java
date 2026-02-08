package com.langchain4j.level3;

import dev.langchain4j.memory.ChatMemory;
import dev.langchain4j.memory.chat.MessageWindowChatMemory;
//import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.openai.OpenAiChatModel;
import dev.langchain4j.service.AiServices;
import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;
import dev.langchain4j.web.search.WebSearchTool;
import dev.langchain4j.web.search.searchapi.SearchApiWebSearchEngine;

import java.util.HashMap;
import java.util.Map;
import java.util.Scanner;

public class Main {

    interface Assistant {
        @SystemMessage({
                "You are a helpful AI assistant with access to a web search tool.",
                "Always prioritize accuracy, up-to-date facts, and transparency.",
                "",
                "If the user asks a question that involves:",
                "- current events (e.g. elections, news, tech updates)",
                "- time-sensitive info (e.g. today's date, weather, stock prices)",
                "- anything that may have changed recently",
                "then you MUST:",
                "- use the web search tool",
                "- extract the most relevant and trustworthy results",
                "- always include source links in the answer",
                "",
                " Do NOT hallucinate real-time info based on memory.",
                "",
                "For static topics like general knowledge, history, or definitions, you can answer without search.",
                "",
                "Be concise, cite sources, and double-check output."
        })

        @UserMessage("{{it}}")
        String chat(String userMessage);
    }

    public static void main(String[] args) {
        String searchApiKey = System.getenv("SEARCHAPI_KEY");;

        Map<String, Object> optionalParams = new HashMap<>();
        optionalParams.put("gl", "us");
        optionalParams.put("hl", "en");
        optionalParams.put("google_domain", "google.com");

        SearchApiWebSearchEngine searchEngine = SearchApiWebSearchEngine.builder()
                .apiKey(searchApiKey)
                .engine("google")
                .optionalParameters(optionalParams)
                .build();

        WebSearchTool webTool = WebSearchTool.from(searchEngine);

        OpenAiChatModel model = OpenAiChatModel.builder()
                .baseUrl("http://langchain4j.dev/demo/openai/v1")
                .apiKey("demo")
                .modelName("gpt-4o-mini")
                .build();

        ChatMemory memory = MessageWindowChatMemory.builder()
                .maxMessages(10)
                .build();

        Assistant assistant = AiServices.builder(Assistant.class)
                .chatModel(model)
                .chatMemory(memory)
                .tools(webTool)
                .build();

        Scanner scanner = new Scanner(System.in);
        System.out.println("=== Level 3 Agent with SearchApiTool ===");
        System.out.println("Type 'exit' to quit.\n");

        while (true) {
            System.out.print("You: ");
            String input = scanner.nextLine();
            if (input.equalsIgnoreCase("exit")) break;
            String response = assistant.chat(input);
            System.out.println("AI: " + response + "\n");
        }

        scanner.close();
    }
}
