import { google } from '@ai-sdk/google';
import { Agent } from '@mastra/core/agent';

export const baseAgent = new Agent({
  name: 'Base Agent',
  instructions: 'Answer any questions that the user may have on any topic',
  model: google('gemini-1.5-pro-latest'),
  
});
