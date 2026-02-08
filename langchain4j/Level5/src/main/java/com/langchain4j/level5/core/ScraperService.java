package com.langchain4j.level5.core;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class ScraperService {

    public String scrape(String url) {
        try {
            HttpClient client = HttpClient.newHttpClient();
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .GET()
                    .build();

            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                String html = response.body();
                return cleanHtml(html);
            } else {
                System.err.println("HTTP error: " + response.statusCode());
            }
        } catch (Exception e) {
            System.err.println("Error scraping: " + e.getMessage());
        }
        return null;
    }

    private String cleanHtml(String html) {
        return html.replaceAll("(?s)<script.*?>.*?</script>", "")
                .replaceAll("(?s)<style.*?>.*?</style>", "")
                .replaceAll("<[^>]+>", " ")
                .replaceAll("\\s+", " ")
                .trim();
    }
}
