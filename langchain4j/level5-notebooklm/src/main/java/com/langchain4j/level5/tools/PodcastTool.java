package com.langchain4j.level5.tools;

import com.langchain4j.level5.core.PodcastService;
import dev.langchain4j.agent.tool.Tool;

/**
 * LangChain4j tool that wraps PodcastService.
 */
public class PodcastTool {

    private final PodcastService podcastService;

    public PodcastTool(PodcastService podcastService) {
        this.podcastService = podcastService;
    }

    @Tool("Generate a podcast audio file from a dialogue script")
    public String generatePodcast(String script, String outputFile) {
        try {
            podcastService.generatePodcast(script, outputFile);
            return "Podcast generated successfully: " + outputFile;
        } catch (Exception e) {
            return "Error generating podcast: " + e.getMessage();
        }
    }
}
