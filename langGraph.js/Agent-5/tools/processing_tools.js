import { HumanMessage, SystemMessage } from "@langchain/core/messages";
import { tool } from "@langchain/core/tools";
import fs from "fs";
import util from "util";
import textToSpeech from "@google-cloud/text-to-speech";
import { z } from "zod";

export function createTools(llm) {
    const mindMapTool = tool(               // creates a mind map of the source material
    async ({ docContent, query }) => {
        const systemMessage = new SystemMessage(`You are an AI Assistant that helps users create a mind map based on the content provided.
        Return ONLY valid JSON in this structure:
            {
            "title": "<short title>",
            "topics": [
                {
                "title": "<topic>",
                "subtopics": [
                    { "title": "<subtopic>", "subsubtopics": [{"title...//if applicable"}] }
                ]
                }
            ]
            }`
        );
        const response = await llm.invoke([systemMessage ,new HumanMessage(`content : ${docContent} where the query was ${query}`)]);
        const mindMap = response.content;
        await fs.promises.writeFile("mind_map.txt", mindMap);
        return "✅ Mind map saved to mind_map.txt\n" + mindMap;
    },
    {
        name: "MindMapCreation",
        description: "Generate a hierarchical mind-map JSON based on the provided content and user query.",
        schema: z.object({
            query: z.string().describe("The user's query regarding the source material"),
            docContent: z.string().describe("Content extracted from the source material"),
        }),
    }
    );

    const podcastTool = tool(
    async ({ docContent, query }) => {
        // --- STEP 1: Update the LLM Prompt ---
        // Instruct the LLM to write a script with clear speaker labels.
        const systemMessage = new SystemMessage(
        `You are a professional podcast scriptwriter. Your task is to create an engaging conversational script between two speakers (a Host and a Guest) based on the provided content.
        
        IMPORTANT: You MUST format the script with speaker labels on each line. For example:
        Host: "Welcome to the show."
        Guest: "It's great to be here."
        
        Your entire response must be ONLY the script itself. Do not include any other text.`
        );

        const llmResponse = await llm.invoke([
        systemMessage,
        new HumanMessage(`Create a podcast script from this content: ${docContent}, focusing on the query: "${query}"`)
        ]);
        const podcastScript = llmResponse.content;

        // --- STEP 2: Convert the Script to SSML ---
        // We'll parse the script and wrap each line in SSML tags to assign voices.
        const lines = podcastScript.split('\n').filter(line => line.trim() !== '');
        let ssmlBody = '';
        
        for (const line of lines) {
        if (line.startsWith('Host:')) {
            // Assign a male voice to the Host
            const dialogue = line.replace('Host:', '').trim();
            ssmlBody += `<voice name="en-US-Wavenet-D">${dialogue}</voice>`;
        } else if (line.startsWith('Guest:')) {
            // Assign a female voice to the Guest
            const dialogue = line.replace('Guest:', '').trim();
            ssmlBody += `<voice name="en-US-Wavenet-F">${dialogue}</voice>`;
        }
        }
        
        // The final SSML string must be wrapped in <speak> tags.
        const finalSSML = `<speak>${ssmlBody}</speak>`;

        // --- STEP 3: Update the Google Cloud TTS API Call ---
        const client = new textToSpeech.TextToSpeechClient({ keyFilename: "gcp-tts.json" });
        const request = {
        // Tell the API we are sending SSML, not plain text
        input: { ssml: finalSSML },
        // The voice config here acts as a default but is overridden by the <voice> tags in our SSML
        voice: { languageCode: "en-US" },
        audioConfig: { audioEncoding: "MP3" },
        };
        
        const [result] = await client.synthesizeSpeech(request);
        const writeFile = util.promisify(fs.writeFile);
        await writeFile("podcast_episode_two_voice.mp3", result.audioContent, "binary");
        
        return "✅ A two-voice podcast has been created and saved to podcast_episode_two_voice.mp3";
    },
    {
        name: "PodcastCreation",
        description: "Generates a two-voice conversational podcast script based on the provided content and user query, then converts it to audio.",
        schema: z.object({
        query: z.string().describe("The user's query regarding the source material"),
        docContent: z.string().describe("Content extracted from the source material"),
        }),
    }
    );

    const noteTakingTool= tool(             // creates bullet notes of the source material 
    async ({docContent, query}) => {      
        const response = await llm.invoke([
            new SystemMessage("You are an AI assistant that helps user make bullet points notes of the context provided. Based on the content provided, give proper brief and concise notes"),                            
            new HumanMessage(`Here is the content: ${docContent} and here is the query used: ${query}`)
        ]);

        return `Here are the notes you requested:\n${response.content}`;
    },{
        name: "NoteTaking",
        description: "Generates concise notes based on the provided content and user query.",
        schema: z.object({
            docContent: z.string().describe("Content extracted from the source material"),
            query: z.string().describe("The user's query regarding the source material"),
        }),
        }
    );

    const summarizationTool = tool(          // summarizes the source material 
    async ({docContent, query}) => {  
        const summaryPrompt = [
        {
            role: "system",
            content:
            "Summarize the following text clearly and concisely for the user.",
            },
            {
            role: "user",
            content: `Content: ${docContent} and here is the query used: ${query}`,
        },
        ];
        const response = await llm.invoke(summaryPrompt);
        return `Here is the summary you requested:\n${response.content}`;
    },
    {
        name: "Summarization",
        description: "Summarizes the provided content based on the user's query.",
        schema: z.object({
            query: z.string().describe("The user's query regarding the source material"),
            docContent : z.string().describe("Content extracted from the source material"),
        }),
    }
    );
    return [mindMapTool, podcastTool, noteTakingTool, summarizationTool];
}