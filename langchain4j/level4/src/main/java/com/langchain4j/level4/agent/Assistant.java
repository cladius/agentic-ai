package com.langchain4j.level4.agent;

import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;
import dev.langchain4j.service.V;

public interface Assistant {
    @SystemMessage({
            "You are a document question answering assistant.",
            "Use the provided document context to answer.",
            "ONLY use the web search tool when the user asks to search online",
            "If the query includes phrases like 'search online for []' or 'find info on []', you MUST use the web search tool.",
            "Do not use the web search tool for any other type of question."
    })
    @UserMessage("Context:\n{{context}}\n\nQuestion:\n{{question}}")
    String answer(@V("context") String context, @V("question") String question);
}
