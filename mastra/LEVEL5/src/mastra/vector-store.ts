import { LibSQLVector } from '@mastra/libsql';
import dotenv from 'dotenv';

dotenv.config();

const { DATABASE_URL, DATABASE_AUTH_TOKEN } = process.env;

if (!DATABASE_AUTH_TOKEN) {
  console.error('ERROR: DATABASE_AUTH_TOKEN is required');
  process.exit(1);
}

export const store = new LibSQLVector({
  connectionUrl: DATABASE_URL || 'libsql://mastra-psl-meghna-m.aws-ap-south-1.turso.io',
  authToken: DATABASE_AUTH_TOKEN
});

export const initializeStore = async () => {
  try {
    console.log('Connecting to vector store...');
    await store.createIndex({
      indexName: 'embeds',
      dimension: 768,
    });
    
    console.log('Vector store index created/verified successfully');
  } catch (error: any) {
    if (error.message?.includes('already exist')) {
      console.log('Index already exists - this is normal');
    } else {
      console.error('Vector store error:', error.message);
    }
  }
};

initializeStore();