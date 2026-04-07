package com.langchain4j.level1;

import dev.langchain4j.model.openai.OpenAiChatModel;
import dev.langchain4j.service.AiServices;
import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;

import java.util.Scanner;

public class Main {

    interface Assistant {
        @SystemMessage("You are a helpful assistant.")
        @UserMessage("{{it}}")
        String chat(String userMessage);
    }

    public static void main(String[] args) {
        OpenAiChatModel model = OpenAiChatModel.builder()
                .baseUrl("http://langchain4j.dev/demo/openai/v1")
                .apiKey("demo")
                .modelName("gpt-4o-mini")
                .build();

        Assistant assistant = AiServices.create(Assistant.class, model);

        Scanner scanner = new Scanner(System.in);

        System.out.println("=== LangChain4j Level 1 Agent ===");
        System.out.println("Type 'exit' to quit.\n");

        while (true) {
            System.out.print("You: ");
            String userMessage = scanner.nextLine();

            if (userMessage.equalsIgnoreCase("exit")) {
                System.out.println("Exiting.");
                break;
            }

            String response = assistant.chat(userMessage);
            System.out.println("AI: " + response);
        }

        scanner.close();
    }
}
