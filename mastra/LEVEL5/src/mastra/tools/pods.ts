import { createTool, ToolExecutionContext } from "@mastra/core";
import { z } from "zod";
import fs from "fs";
import path from "path";
import textToSpeech from "@google-cloud/text-to-speech";
import ffmpeg from "fluent-ffmpeg";
import ffmpegPath from "ffmpeg-static";
import ffprobePath from "ffprobe-static";

if (!ffmpegPath) {
  throw new Error("FFmpeg binary not found. Make sure ffmpeg-static is installed.");
}
ffmpeg.setFfmpegPath(ffmpegPath);
ffmpeg.setFfprobePath(ffprobePath.path);

const client = new textToSpeech.TextToSpeechClient();

const podcastInput = z.object({
  title: z.string(),
  script: z.string().describe(`
Full podcast text. Format like:
Host: Welcome everyone to our show.
Guest: Thanks for having me!
Host: Let’s dive into the topic...
  `),
  voices: z
    .object({
      host: z.string().default("en-US-Neural2-F"),  // female
      guest: z.string().default("en-US-Neural2-D"), // male
    })
    .optional(),
});

type PodcastCtx = ToolExecutionContext<typeof podcastInput>;

export const podcastTool = createTool({
  id: "podcastTool",
  description: "Generate a multi-speaker podcast using Google Cloud Text-to-Speech.",
  inputSchema: podcastInput,

  execute: async (ctx: PodcastCtx) => {
    const { title, script, voices } = ctx.context;
    const { host, guest } = {
      host: "en-US-Neural2-F",
      guest: "en-US-Neural2-D",
      ...(voices || {}),
    };

    const outputDir = path.resolve("podcasts");
    if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });
    const safeTitle = title.replace(/[^\w\s-]/g,"").replace(/\s+/g, "_").toLowerCase();
    const basePath = path.join(outputDir, safeTitle);

    const segments = script.split(/\r?\n+/).map(line=> line.trim()).filter(line => /^\s*(Host|Guest)\s*:/i.test(line));
    const audioSegments: string[] = [];

    for (let i = 0; i < segments.length; i++) {

      const [speaker, ...contentArr] = segments[i].split(":");
      const text = contentArr.join(":").trim();
      const voiceName = speaker.toLowerCase().includes("guest") ? guest : host;

      const request = {
        input: { text },
        voice: { languageCode: "en-US", name: voiceName },
        audioConfig: { audioEncoding: "MP3" as const },
      };

      const [response] = await client.synthesizeSpeech(request);
      const audioPath = `${basePath}_${i}.mp3`;
      fs.writeFileSync(audioPath, response.audioContent!, "binary");
      audioSegments.push(audioPath);
    }

    const finalPath = `${basePath}_final.mp3`;

    await new Promise<void>((resolve, reject) => {
      const command = ffmpeg();
      audioSegments.forEach((seg) => command.input(seg));
      command
        .on("end", () => resolve())
        .on("error", reject)
        .mergeToFile(finalPath, outputDir);
    });

    audioSegments.forEach((seg) => fs.unlinkSync(seg));

    return {
      success: true,
      message: `Two-speaker podcast created successfully: ${finalPath}`,
      path: finalPath,
    };
  },
});
