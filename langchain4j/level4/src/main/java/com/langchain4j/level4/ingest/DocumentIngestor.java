package com.langchain4j.level4.ingest;

import dev.langchain4j.data.document.Metadata;
import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.data.embedding.Embedding;
import dev.langchain4j.store.embedding.weaviate.WeaviateEmbeddingStore;
import net.sourceforge.tess4j.Tesseract;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.rendering.PDFRenderer;
import dev.langchain4j.data.document.Document;
import dev.langchain4j.data.document.DocumentParser;
import dev.langchain4j.data.document.DocumentSplitter;
import dev.langchain4j.data.document.parser.TextDocumentParser;
import dev.langchain4j.data.document.splitter.DocumentSplitters;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class DocumentIngestor {

    private final EmbeddingModel embeddingModel;
    private final WeaviateEmbeddingStore embeddingStore;

    public DocumentIngestor(EmbeddingModel embeddingModel, WeaviateEmbeddingStore embeddingStore) {
        this.embeddingModel = embeddingModel;
        this.embeddingStore = embeddingStore;
    }

    public void ingest(File file) {
        try (PDDocument pdf = PDDocument.load(file)) {
            Tesseract tesseract = new Tesseract();
            tesseract.setDatapath("C:\\Program Files\\Tesseract-OCR\\tessdata");
            tesseract.setLanguage("eng");

            PDFRenderer renderer = new PDFRenderer(pdf);
            DocumentParser parser = new TextDocumentParser();
            DocumentSplitter splitter = DocumentSplitters.recursive(500, 50);
            Instant timestamp = Instant.now();
            String source = file.getName();

            for (int page = 0; page < pdf.getNumberOfPages(); ++page) {
                BufferedImage image = renderer.renderImageWithDPI(page, 400);
                File tempImage = new File("temp_page_" + page + ".png");
                ImageIO.write(image, "png", tempImage);
                String ocrText = tesseract.doOCR(tempImage);
                tempImage.delete();

                ByteArrayInputStream inputStream = new ByteArrayInputStream(ocrText.getBytes(StandardCharsets.UTF_8));
                Document document = parser.parse(inputStream);
                List<TextSegment> segments = splitter.split(document);

                int chunkIndex = 0;
                for (TextSegment segment : segments) {
                    System.out.println("Uploading chunk text:\n" + segment.text() + "\n");
                    Embedding embedding = embeddingModel.embed(segment.text()).content();
                    Map<String, Object> meta = new HashMap<>();
                    meta.put("source", source);
//                    meta.put("page", page + 1);
                    meta.put("chunk_index", chunkIndex);
                    meta.put("timestamp", timestamp.toString());
                    Metadata metadata = Metadata.from(meta);
                    TextSegment segmentWithMetadata = TextSegment.from(segment.text(), metadata);

                    embeddingStore.add(embedding, segmentWithMetadata);

                    chunkIndex++;
                }
            }

            System.out.println("Ingested into Weaviate: " + file.getName());

        } catch (Exception e) {
            System.err.println("Failed to ingest file: " + file.getName());
            e.printStackTrace();
        }
    }
}
