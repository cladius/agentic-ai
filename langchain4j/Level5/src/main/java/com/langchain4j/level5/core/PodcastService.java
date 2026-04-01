package com.langchain4j.level5.core;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.file.*;
import java.util.*;

public class PodcastService {

    private static final String ELEVENLABS_API_KEY = System.getenv("ELEVEN");
    private static final String ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech/";

    private final Map<String, String> speakerVoices = new HashMap<>();
    private final Path cacheDir = Paths.get("podcast_cache");
    private final Path podcastDir = Paths.get("podcasts");

    public PodcastService() throws IOException {
        speakerVoices.put("Host", "EXAVITQu4vr4xnSDxMaL");
        speakerVoices.put("Guest", "ErXwobaYiN019PkySvjV");

        if (!Files.exists(cacheDir)) {
            Files.createDirectories(cacheDir);
        }
        if (!Files.exists(podcastDir)) {
            Files.createDirectories(podcastDir);
        }
    }

    public String generatePodcast(String script, String outputFile) throws Exception {

        // Ensure .mp3 extension
        if (!outputFile.toLowerCase().endsWith(".mp3")) {
            outputFile += ".mp3";
        }

        // Always save into /podcasts
        Path finalPath = podcastDir.resolve(outputFile);

        List<Path> audioFiles = new ArrayList<>();
        int lineNum = 1;

        for (String line : script.split("\n")) {
            if (!line.contains(":")) continue;

            String speaker = line.substring(0, line.indexOf(":")).trim();
            String text = line.substring(line.indexOf(":") + 1).trim();
            String voiceId = speakerVoices.getOrDefault(speaker, speakerVoices.get("Host"));

            // Cache per line
            String cacheFileName = "line_" + lineNum + "_" + Math.abs(text.hashCode()) + ".mp3";
            Path cachedPath = cacheDir.resolve(cacheFileName);

            if (!Files.exists(cachedPath)) {
                synthesizeSpeech(voiceId, text, cachedPath);
            }

            audioFiles.add(cachedPath);
            lineNum++;
        }

        concatenateAudio(audioFiles, finalPath);

        return finalPath.toAbsolutePath().toString();
    }

    private void synthesizeSpeech(String voiceId, String text, Path outPath) throws Exception {
        URL url = new URL(ELEVENLABS_API_URL + voiceId);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setRequestProperty("xi-api-key", ELEVENLABS_API_KEY);
        conn.setRequestProperty("Content-Type", "application/json");
        conn.setRequestProperty("Accept", "audio/mpeg");
        conn.setDoOutput(true);

        String jsonBody = "{\"text\":\"" + text + "\"}";
        try (OutputStream os = conn.getOutputStream()) {
            os.write(jsonBody.getBytes());
        }

        try (InputStream is = conn.getInputStream();
             OutputStream fos = Files.newOutputStream(outPath)) {
            byte[] buf = new byte[4096];
            int len;
            while ((len = is.read(buf)) != -1) {
                fos.write(buf, 0, len);
            }
        }

        conn.disconnect();
    }

    private void concatenateAudio(List<Path> files, Path outputFile) throws IOException, InterruptedException {
        Path listFile = Files.createTempFile("files", ".txt");

        try (BufferedWriter writer = Files.newBufferedWriter(listFile)) {
            for (Path p : files) {
                writer.write("file '" + p.toAbsolutePath().toString().replace("\\", "\\\\") + "'\n");
            }
        }

        new ProcessBuilder(
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", listFile.toString(),
                "-c", "copy",
                outputFile.toString()
        )
                .inheritIO()
                .start()
                .waitFor();

        Files.deleteIfExists(listFile);
    }
}
