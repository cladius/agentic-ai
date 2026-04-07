package com.langchain4j.level5.tools;

import com.langchain4j.level5.core.MindmapService;
import dev.langchain4j.agent.tool.Tool;

import java.util.List;

public class MindMapTool {

    private final MindmapService service;

    public MindMapTool(MindmapService service) {
        this.service = service;
    }

    @Tool(
            name = "makeMindmap",
            value = "Generate a mindmap image from lines formatted as 'Root:Child1,Child2,...'. Returns the file path."
    )
    public String makeMindmap(List<String> lines) {
        try {
            return service.makeMindmap(lines);
        } catch (Exception e) {
            throw new RuntimeException("Mindmap generation failed: " + e.getMessage(), e);
        }
    }
}
