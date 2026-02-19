
import { Mastra } from '@mastra/core/mastra';
import { baseAgent } from './agents/base-agent';

export const mastra = new Mastra({
  agents: { baseAgent },
  
});
