import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { YoutubeLoader } from "@langchain/community/document_loaders/web/youtube";
import { PDFLoader } from "@langchain/community/document_loaders/fs/pdf";
import { RecursiveUrlLoader } from "@langchain/community/document_loaders/web/recursive_url";
import { compile } from "html-to-text";

export function createIngestionTools() {

  const youtubeTool = tool(async (url) => { 
  // Ingest YouTube video transcript
    try {
      console.log(`[Tool] Ingesting YouTube URL: ${url}`);
      // YoutubeLoader- Fetches and parses transcripts from a YouTube video.
      const loader = YoutubeLoader.createFromUrl(url, { language: "en", addVideoInfo: false });
      // `addVideoInfo: false` avoids loading metadata, reducing output noise.

      const docs = await loader.load();
      return docs.map(doc => doc.pageContent).join('\n\n'); // Combine pages into a single text block.
    } catch (e) { return `Error loading YouTube URL: ${e.message}`; }
  }, {
    name: "youtube_ingestion_tool",
    description: "Extracts the transcript from a YouTube video URL.",
    schema: z.string().describe("The full URL of the YouTube video."),
  });

  const webpageTool = tool(async (url) => {
    // Ingest webpage content
    try {
      console.log(`[Tool] Ingesting Webpage URL: ${url}`);

      /* RecursiveUrlLoader: 
      Loads webpage content by crawling a URL and optionally following links on the webpage recursively. 
      It fetches the HTML content of each page, processes it into text using a custom extractor, 
      and returns it as a collection of documents. The maxDepth option controls how deep the crawler navigates.
      `compile` converts HTML to clean plaintext.
      The wordwrap: 130 option ensures that long lines are wrapped at approximately 130 characters, producing clean, formatted text.
      `maxDepth: 0` prevents recursive crawling (extracts only the provided page).
      */
      const loader = new RecursiveUrlLoader(url, { extractor: compile({ wordwrap: 130 }), maxDepth: 0 });
      const docs = await loader.load();
      return docs.map(doc => doc.pageContent).join('\n\n');
    } catch (e) { return `Error loading webpage: ${e.message}`; }
  }, {
    name: "webpage_ingestion_tool",
    description: "Extracts the text content from a webpage URL.",
    schema: z.string().describe("The full URL of the webpage."),
  });

  const pdfTool = tool(async (filePath) => {
  // Loads the PDF from a file path and extracts its text
    try {
      console.log(`[Tool] Ingesting PDF: ${filePath}`);
      // PDFLoader- Loads and parses local PDF files, extracting their text content page by page.
      const loader = new PDFLoader(filePath);
      const docs = await loader.load();
      return docs.map(doc => doc.pageContent).join('\n\n');
    } catch (e) { return `Error loading PDF: ${e.message}`; }
  }, {
    name: "pdf_ingestion_tool",
    description: "Extracts the text content from a local PDF file path.",
    schema: z.string().describe("The local file path to the PDF."),
  });

  const textContentTool = tool(async (text) => {
  // Ingest raw text directly from user input. Useful for pasting content directly instead of using files or URLs.
    console.log("[Tool] Storing direct text input.");
    return text;
  }, {
    name: "text_ingestion_tool",
    description: "Stores direct text provided by the user as a resource.",
    schema: z.string().describe("The raw text content to be used as a resource."),
  });

  // Export all ingestion tools so they can be registered with an agent.  
  return [youtubeTool, webpageTool, pdfTool, textContentTool];
}