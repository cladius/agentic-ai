package com.langchain4j.level5.core;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;

public class YoutubeService {
    private static final String YT_DLP_PATH = "yt-dlp";
    private static final String OUTPUT_TEMPLATE = "%(id)s.%(ext)s";

    public static class IngestResult {
        public final String videoId;
        public final String transcript;

        public IngestResult(String videoId, String transcript) {
            this.videoId = videoId;
            this.transcript = transcript;
        }
    }

    public IngestResult ingest(String videoUrl) throws IOException, InterruptedException {
        String cleanUrl = stripPlaylistParams(videoUrl);

        List<String> command = Arrays.asList(
                YT_DLP_PATH,
                "--no-playlist",
                "--write-auto-sub",
                "--skip-download",
                "--sub-lang", "en",
                "--convert-subs", "vtt",
                "--output", OUTPUT_TEMPLATE,
                cleanUrl
        );

        ProcessBuilder pb = new ProcessBuilder(command);
        pb.redirectErrorStream(true);

        Process process = pb.start();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                System.out.println("[yt-dlp] " + line);
            }
        }

        if (!process.waitFor(120, TimeUnit.SECONDS)) {
            process.destroy();
            throw new RuntimeException("yt-dlp process timed out");
        }

        if (process.exitValue() != 0) {
            throw new RuntimeException("yt-dlp failed with exit code " + process.exitValue());
        }
        String videoId = extractVideoId(cleanUrl);
        Path vttPath = Paths.get(videoId + ".en.vtt");
        if (!Files.exists(vttPath)) {
            throw new FileNotFoundException("Subtitle file not found: " + vttPath.toAbsolutePath());
        }

        String vttContent = Files.readString(vttPath, StandardCharsets.UTF_8);

        try {
            Files.delete(vttPath);
        } catch (IOException ignored) {}

        String transcript = vttToCleanText(vttContent);

        return new IngestResult(videoId, transcript);
    }

    private String stripPlaylistParams(String url) {

        return url.replaceAll("&list=[^&]+", "").replaceAll("&index=\\d+", "");
    }

    private String extractVideoId(String url) {
        String pattern = "(?:v=|youtu\\.be/)([a-zA-Z0-9_-]{11})";
        java.util.regex.Matcher matcher = java.util.regex.Pattern.compile(pattern).matcher(url);
        if (matcher.find()) {
            return matcher.group(1);
        }
        throw new IllegalArgumentException("Could not extract video ID from URL: " + url);
    }

    private String vttToCleanText(String vttContent) {
        // Remove WEBVTT header
        vttContent = vttContent.replaceFirst("(?i)^WEBVTT.*\\n", "");

        // Remove HTML-like tags
        vttContent = vttContent.replaceAll("<[^>]+>", "");

        // Remove timestamps
        vttContent = vttContent.replaceAll("\\d{2}:\\d{2}:\\d{2}\\.\\d{3} --> .*", "");

        // Remove cue numbers
        vttContent = vttContent.replaceAll("^\\d+\\s*$", "");

        // Collapse whitespace
        vttContent = vttContent.replaceAll("[ \\t]+", " ").replaceAll("\\s*\\n\\s*", "\n").trim();

        // Split into sentences, remove duplicates while preserving order
        Set<String> uniqueSentences = new LinkedHashSet<>();
        for (String line : vttContent.split("(?<=[.!?])\\s+|\\n")) {
            String cleaned = line.trim();
            if (!cleaned.isEmpty()) {
                uniqueSentences.add(cleaned);
            }
        }

        return String.join(" ", uniqueSentences);
    }
}
