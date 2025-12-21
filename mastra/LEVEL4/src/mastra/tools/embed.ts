import { MDocument } from '@mastra/rag';
import { GoogleGenerativeAI } from '@google/generative-ai';
import { store } from '../vector-store';

const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY!);

export const chunkembedDocuments = {
  name: 'Chunk and Embed Documents',
  description: 'Chunk and embed documents for vector storage',
  parameters: {
    type: 'object',
    properties: {
      documents: {
        type: 'array',
        description: 'Array of MDocument objects to process'
      }
    },
    required: ['documents']
  },

  execute: async ({ documents }: { documents: MDocument[] }) => {
    const results: any[] = [];

    for (const mdoc of documents) {
      try {
        console.log('Document properties:', Object.keys(mdoc));
        
        const chunks = await mdoc.chunk();
        const model = genAI.getGenerativeModel({ model: "text-embedding-004" });

        const texts = await Promise.all(
          chunks.map(async (chunk) => await chunk.getText()) 
        );

        const embeddings = await Promise.all(
          texts.map(async (text) => {
            const result = await model.embedContent(text);
            return result.embedding.values;
          })
        );

        // Try to access metadata
        const docMetadata = (mdoc as any).metadata || {};

        const vectorIds = embeddings.map((_, index) => 
          `${docMetadata.filename || 'doc'}_chunk_${index}`
        );

        const vectorMetadata = embeddings.map((_, index) => ({
          text: texts[index],
          filename: docMetadata.filename,
          uploadedAt: docMetadata.uploadedAt,
          fileSize: docMetadata.fileSize,
          chunkIndex: index,
          totalChunks: chunks.length,
          model: 'text-embedding-004'
        }));

        // Use your original format - it was probably correct
        await store.upsert({
          indexName: 'embeds',
          vectors: embeddings,
          metadata: vectorMetadata,
          ids: vectorIds
        });

        // const sampleText = texts[0];
        // const sanity = await store.query({
        //   indexName: 'embeds',
        //   queryVector: embeddings[0],
        //   topK: 1
        // });
        // console.log('Sanity check retrieval:', sanity);


        results.push({
          filename: docMetadata.filename || 'unknown',
          chunksCreated: chunks.length,
          status: 'processed'
        });

      } catch (error: any) {
        console.error('Error during embedding:', error);
        results.push({
          filename: 'unknown',
          status: 'error',
          error: error.message
        });
      }
    }

    return { 
      success: true,
      totalDocuments: documents.length,
      successfullyProcessed: results.filter(r => r.status === 'processed').length,
      errors: results.filter(r => r.status === 'error').length,
      details: results 
    };
  }
};