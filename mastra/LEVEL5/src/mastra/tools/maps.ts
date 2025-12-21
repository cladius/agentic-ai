import { createTool, ToolExecutionContext } from "@mastra/core";
import { z } from "zod";
import fs from "fs";
import path from "path";
import puppeteer from "puppeteer";

const mindMapInput = z.object({
  topic: z.string(),
  content: z.string().describe("Mermaid mind map syntax starting with 'mindmap'"),
});

type FixedCtx = ToolExecutionContext<typeof mindMapInput>;

export const generateMindMap = createTool({
  id: "generateMindMap",
  description: "Render a full high-resolution Mermaid mind map and save it as PNG.",
  inputSchema: mindMapInput,
  execute: async (ctx: FixedCtx) => {
    const { topic, content } = ctx.context;

    // ✅ Embed Mermaid client-side renderer
    const html = `<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <style>
      body {
        margin: 0;
        background: white;
        display: flex;
        justify-content: center;
        align-items: center;
        overflow: visible;
      }
      #container {
        padding: 2rem;
      }
      svg {
        font-family: Arial, sans-serif;
      }
    </style>
  </head>
  <body>
    <div id="container"></div>
    <script type="module">
      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
      mermaid.initialize({ startOnLoad: false, theme: 'default' });
      const graph = \`${content}\`;
      mermaid.render('mindmap', graph).then(({ svg }) => {
        const el = document.getElementById('container');
        el.innerHTML = svg;
      });
    </script>
  </body>
</html>`;

    const browser = await puppeteer.launch({
      headless: true,
      args: ["--no-sandbox", "--disable-setuid-sandbox"],
      defaultViewport: { width: 1920, height: 1080, deviceScaleFactor: 4 },
    });

    const page = await browser.newPage();
    await page.setContent(html, { waitUntil: "networkidle0" });

    // Wait for rendering
    await page.waitForSelector("svg", { timeout: 20000 });
    const dimensions = await page.evaluate(() => {
      const svg = document.querySelector("svg");
      if (!svg) return null;
      const rect = svg.getBBox();
      return { width: rect.width + 100, height: rect.height + 100 };
    });

    if (!dimensions) throw new Error("Failed to measure SVG size.");

    await page.setViewport({
      width: Math.ceil(dimensions.width),
      height: Math.ceil(dimensions.height),
      deviceScaleFactor: 4,
    });

    const svgElement = await page.$("svg");
    if (!svgElement) throw new Error("SVG not found for screenshot.");

    const outputDir = path.resolve("mindmaps");
    if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });
    const safeTopic = topic.replace(/\s+/g, "_").toLowerCase();
    const pngPath = path.join(outputDir, `${safeTopic}_full_hd.png`);

    await svgElement.screenshot({
      path: pngPath as `${string}.png`,
      omitBackground: false,
    });

    await browser.close();

    return {
      success: true,
      message: `Full mind map saved at ${pngPath}`,
      path: pngPath,
    };
  },
});
