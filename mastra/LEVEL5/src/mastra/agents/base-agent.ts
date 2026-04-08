import { google } from '@ai-sdk/google';
import { Agent } from '@mastra/core/agent';
import { Memory } from '@mastra/memory';
import { LibSQLStore } from '@mastra/libsql';
import { GoogleVoice } from '@mastra/voice-google';
import { createGoogleDocTool, writeGoogleDocTool } from '../tools/docs';
import { vectorQueryTool } from '../tools/vectorquery';
import { generateMindMap } from '../tools/maps';
import { podcastTool } from '../tools/pods';

const voice = new GoogleVoice();

export const baseAgent = new Agent({
  name: 'Base Agent',
  instructions: `Answer any questions that the user may have on any topic.
  When users ask questions about documents they've uploaded, 
  use the vectorQueryTool to search through the embedded content 
  When the user requests a mind map (e.g. "create a mind map of the French Revolution" or "show relationships in photosynthesis using a mind map")
  Do not ask the user for nodes, titles, or structure — infer them yourself, generate a valid Mermaid mind map syntax and 
  call the 'generateMindMap' tool with it. .
  Always ensure that your responses are accurate and relevant to the user's queries.
  When users ask to create a podcast (e.g. "make a podcast about AI ethics"),
  first write a short, conversational script (2–4 minutes long with a host and a guest) with a friendly tone.
  Then, call the 'podcastTool' tool with:
    - title: inferred from the topic
    - script: your generated podcast script text.
    
  Example:
  title: "The Future of AI Ethics"
  script: "Host: Welcome to our show... etc."
  Do not provide host/guest names — use the default voices. Once it's create just inform the user that it can be found in the output/podcasts directory.
  `,
  model: google('gemini-2.5-pro'),
  
  memory: new Memory({
    storage: new LibSQLStore({
      url: 'file:../mastra.db',
    }),
    options:{
      workingMemory:{ 
        enabled: true,
        scope: "resource"
      },
    },
  }),
  voice: voice,
  //maxSteps: 20,
  tools: { createGoogleDocTool, writeGoogleDocTool, vectorQueryTool, generateMindMap, podcastTool},
});
