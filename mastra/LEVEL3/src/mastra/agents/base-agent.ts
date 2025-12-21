import { google } from '@ai-sdk/google';
import { Agent } from '@mastra/core/agent';
import { Memory } from '@mastra/memory';
import { LibSQLStore } from '@mastra/libsql';
import { GoogleVoice } from '@mastra/voice-google';
import { createGoogleDocTool, writeGoogleDocTool } from '../tools/docs';

const voice = new GoogleVoice();

export const baseAgent = new Agent({
  name: 'Base Agent',
  instructions: 'Answer any questions that the user may have on any topic',
  model: google('gemini-1.5-pro-latest'),
  
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
  tools: { createGoogleDocTool, writeGoogleDocTool},
});
