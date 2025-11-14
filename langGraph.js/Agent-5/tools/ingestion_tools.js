import { tool } from "@langchain/core/tools";
import { z } from "zod";
import { YoutubeLoader } from "@langchain/community/document_loaders/web/youtube";
import { PDFLoader } from "@langchain/community/document_loaders/fs/pdf";
import { RecursiveUrlLoader } from "@langchain/community/document_loaders/web/recursive_url";
import { compile } from "html-to-text";

export function createIngestionTools() {
  const youtube_tool = tool(async (url) => {
    try {
      console.log(`[Tool] Ingesting YouTube URL: ${url}`);
      const loader = YoutubeLoader.createFromUrl(url, { language: "en", addVideoInfo: false });
      const docs = await loader.load();
      return docs.map(doc => doc.pageContent).join('\n\n');
    } catch (e) { return `Error loading YouTube URL: ${e.message}`; }
  }, {
    name: "youtube_ingestion_tool",
    description: "Extracts the transcript from a YouTube video URL.",
    schema: z.string().describe("The full URL of the YouTube video."),
  });

  const webpage_tool = tool(async (url) => {
    try {
      console.log(`[Tool] Ingesting Webpage URL: ${url}`);
      const loader = new RecursiveUrlLoader(url, { extractor: compile({ wordwrap: 130 }), maxDepth: 0 });
      const docs = await loader.load();
      return docs.map(doc => doc.pageContent).join('\n\n');
    } catch (e) { return `Error loading webpage: ${e.message}`; }
  }, {
    name: "webpage_ingestion_tool",
    description: "Extracts the text content from a webpage URL.",
    schema: z.string().describe("The full URL of the webpage."),
  });

  const pdf_tool = tool(async (filePath) => {
    try {
      console.log(`[Tool] Ingesting PDF: ${filePath}`);
      const loader = new PDFLoader(filePath);
      const docs = await loader.load();
      return docs.map(doc => doc.pageContent).join('\n\n');
    } catch (e) { return `Error loading PDF: ${e.message}`; }
  }, {
    name: "pdf_ingestion_tool",
    description: "Extracts the text content from a local PDF file path.",
    schema: z.string().describe("The local file path to the PDF."),
  });

  const text_content_tool = tool(async (text) => {
    console.log("[Tool] Storing direct text input.");
    return text;
  }, {
    name: "text_ingestion_tool",
    description: "Stores direct text provided by the user as a resource.",
    schema: z.string().describe("The raw text content to be used as a resource."),
  });
  
  return [youtube_tool, webpage_tool, pdf_tool, text_content_tool];
}