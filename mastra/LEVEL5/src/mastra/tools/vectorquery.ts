import { z } from 'zod';
import { GoogleGenerativeAI } from '@google/generative-ai';
import { store } from '../vector-store';

export const vectorQueryTool = {
  name: 'vectorQuery',
  id: 'vectorQuery',
  description: 'Search through uploaded documents for relevant information',
  inputSchema: z.object({
    query: z.string().describe('The search query to find relevant documents'),
    topK: z.number().default(5).describe('Number of results to return'),
  }),
  execute: async ({ query, topK }: { query: string; topK: number }) => {
    try {
      const model = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY!).getGenerativeModel({ model: "text-embedding-004" });
      const embedding = await model.embedContent(query);
      
      // Search using the embedding
      const results = await store.query({
        indexName: 'embeds',
        queryVector: embedding.embedding.values,
        topK: topK
      });
      
      return {
        success: true,
        query: query,
        resultsCount: results.length,
        results: results.map(result => ({
          text: result.metadata?.text || result.metadata?.content,
          score: result.score,
          filename: result.metadata?.filename,
          chunkIndex: result.metadata?.chunkIndex
        }))
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Search failed'
      };
    }
  }
};