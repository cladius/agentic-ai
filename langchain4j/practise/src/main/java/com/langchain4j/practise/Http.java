package com.langchain4j.practise;

import dev.langchain4j.memory.ChatMemory;
import dev.langchain4j.memory.chat.MessageWindowChatMemory;
import dev.langchain4j.mcp.McpToolProvider;
import dev.langchain4j.mcp.client.DefaultMcpClient;
import dev.langchain4j.mcp.client.McpClient;
import dev.langchain4j.mcp.client.transport.McpTransport;
import dev.langchain4j.mcp.client.transport.http.HttpMcpTransport;
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.openai.OpenAiChatModel;
import dev.langchain4j.service.AiServices;
import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.tool.ToolProvider;

import java.time.Duration;
import java.util.List;
import java.util.Scanner;

public class Http {
    interface Assistant {
        @SystemMessage("""
                You are a helpful assistant with memory.
                You have a tool that can add two numbers.
                When asked to perform addition, you must use this tool.
                """)
        String chat(String userMessage);
    }

    public static void main(String[] args) throws Exception {

        ChatModel model = OpenAiChatModel.builder()
                .baseUrl("http://langchain4j.dev/demo/openai/v1")
                .apiKey("demo")
                .modelName("gpt-4o-mini")
                .build();

        McpTransport transport = new HttpMcpTransport.Builder()
                .sseUrl("http://localhost:3001/sse")
                .timeout(Duration.ofSeconds(60))
                .logRequests(true)
                .logResponses(true)
                .build();

        McpClient mcpClient = new DefaultMcpClient.Builder()
                .transport(transport)
                .build();

        ToolProvider toolProvider = McpToolProvider.builder()
                .mcpClients(List.of(mcpClient))
                .build();

        ChatMemory memory = MessageWindowChatMemory.builder()
                .maxMessages(10)
                .build();

        Assistant assistant = AiServices.builder(Assistant.class)
                .chatModel(model)
                .toolProvider(toolProvider)
                .chatMemory(memory)
                .build();

        Scanner scanner = new Scanner(System.in);
        try {
            System.out.println("=== LangChain4j Agent with HTTP MCP Tools & Memory ===");
            System.out.println("Type 'exit' to quit.\n");
            // Example command: "What is 234 + 567?"

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
        } finally {
            // 7. Clean up resources
            mcpClient.close();
            scanner.close();
        }
    }
}