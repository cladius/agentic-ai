import { google } from '@ai-sdk/google';
import { Agent } from '@mastra/core/agent';
import { Memory } from '@mastra/memory';
import { LibSQLStore } from '@mastra/libsql';
import { GoogleVoice } from '@mastra/voice-google';
import { createGoogleDocTool, writeGoogleDocTool } from '../tools/docs';
import { vectorQueryTool } from '../tools/vectorquery';
import { generateMindMap } from '../tools/maps';

const voice = new GoogleVoice();

export const baseAgent = new Agent({
  name: 'Base Agent',
  instructions: `Answer any questions that the user may have on any topic.
  When users ask questions about documents they've uploaded, 
  use the vectorQueryTool to search through the embedded content 
  When the user requests a mind map (e.g. "create a mind map of the French Revolution" or "show relationships in photosynthesis"):
  1. Generate valid Mermaid mind map syntax.
  2. The diagram must begin with 'mindmap' and use proper indentation to represent relationships.
  3. Then call the generateMindMap tool, passing the generated Mermaid content as 'content' and the topic name as 'topic'.
  Do not ask the user for nodes, titles, or structure — infer them yourself.
  Always ensure that your responses are accurate and relevant to the user's queries.`,
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
  tools: { createGoogleDocTool, writeGoogleDocTool, vectorQueryTool, generateMindMap},
});
