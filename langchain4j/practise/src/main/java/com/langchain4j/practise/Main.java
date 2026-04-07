package com.langchain4j.practise;

import dev.langchain4j.memory.ChatMemory;
import dev.langchain4j.memory.chat.MessageWindowChatMemory;
import dev.langchain4j.mcp.McpToolProvider;
import dev.langchain4j.mcp.client.DefaultMcpClient;
import dev.langchain4j.mcp.client.McpClient;
import dev.langchain4j.mcp.client.transport.McpTransport;
import dev.langchain4j.mcp.client.transport.stdio.StdioMcpTransport;
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.openai.OpenAiChatModel;
import dev.langchain4j.service.AiServices;
import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.tool.ToolProvider;

import java.io.File;
import java.util.List;
import java.util.Scanner;

public class Main {
    interface Assistant {
        @SystemMessage("""
                You are a helpful assistant with memory.
                You have tools to interact with the local filesystem.
                When asked to read a file, provide its absolute path.
                """)
        String chat(String userMessage);
    }

    public static void main(String[] args) throws Exception {

        ChatModel model = OpenAiChatModel.builder()
                .baseUrl("http://langchain4j.dev/demo/openai/v1")
                .apiKey("demo")
                .modelName("gpt-4o-mini")
                .build();

        McpTransport transport = new StdioMcpTransport.Builder()
                .command(List.of("C:\\Program Files\\nodejs\\npm.cmd", "exec",
                        "@modelcontextprotocol/server-filesystem@0.6.2",
                        new File("src/main/resources").getAbsolutePath()
                ))
                .logEvents(true)
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
            System.out.println("=== LangChain4j Agent with MCP Tools & Memory ===");
            System.out.println("Type 'exit' to quit.\n");
            // Example command: "Read the contents of the file file.txt"

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
            mcpClient.close();
            scanner.close();
        }
    }
}