package com.langchain4j.level5;

import com.langchain4j.level5.core.QAService;

import java.io.IOException;

public class Main {
    public static void main(String[] args) throws IOException, InterruptedException {
        QAService qaService = new QAService();
        qaService.startChatLoop();
    }
}
