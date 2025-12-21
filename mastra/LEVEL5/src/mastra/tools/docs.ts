import { google } from 'googleapis';
import path from 'path';
import dotenv from 'dotenv';
import fs from 'fs';
import readline from 'readline';

dotenv.config();

const {
  GOOGLE_CLIENT_ID,
  GOOGLE_CLIENT_SECRET,
  GOOGLE_REDIRECT_URI,
  GOOGLE_TOKEN_PATH
} = process.env;

async function getGoogleAuth() {
  const oAuth2Client = new google.auth.OAuth2(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI);
  const tokenPath= path.resolve(GOOGLE_TOKEN_PATH || './tokens.json');

  if (fs.existsSync(tokenPath)) {
    const token = JSON.parse(fs.readFileSync(tokenPath, 'utf8'));

    if (!token.refresh_token) {
      console.warn('Refresh token missing in token file. Deleting and re-authenticating...');
      fs.unlinkSync(tokenPath);
      return await getGoogleAuth();
    }

    oAuth2Client.setCredentials(token);
    return oAuth2Client;
  }

  const authUrl = oAuth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: ['https://www.googleapis.com/auth/documents',
      'https://www.googleapis.com/auth/drive.file'
    ],
  });

  console.log(' Authorize this app by visiting this URL:\n', authUrl);

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const code = await new Promise<string>((resolve) =>
    rl.question('\n Enter the code from that page here: ', (code) => {
      rl.close();
      resolve(decodeURIComponent(code.trim()));
    })
  );

  const tokenResponse = await oAuth2Client.getToken(code);
  const tokens = tokenResponse.tokens;
  if (!tokens) {
    throw new Error(' Failed to get tokens from code');
  }

  oAuth2Client.setCredentials(tokens);
  fs.writeFileSync(tokenPath, JSON.stringify(tokens, null, 2));
  console.log(`Tokens stored at ${tokenPath}`);

  return oAuth2Client;
}

export const writeGoogleDocTool = {
  name: "writeGoogleDoc",
  id: "writeGoogleDoc",
  description: "Writes content to a Google Doc with a given document title.",
  parameters: {
    type: "object",
    properties: {
      title: { type: "string", description: "Title of the document to write to" },
      content: { type: "string", description: "Content to write in the document" },
    },
    required: ["title", "content"],
  },
  async execute({ title, content }: { title: string; content: string }) {
    const auth = await getGoogleAuth();
    const docs = google.docs({ version: "v1", auth });
    const drive= google.drive({ version: "v3", auth });

    // Find the document by title
    const res = await drive.files.list({
      q: `name='${title}' and mimeType='application/vnd.google-apps.document'`,
    });

    const file = res.data.files?.[0];
    if (!file) {
      return { message: `Document with title "${title}" not found. Would you like me to create a new document?`, };
    }
    const documentId = file.id;

    if (!documentId) {
      throw new Error('Couldn\'t find the document ID for the specified title');
    }
    await docs.documents.batchUpdate({
      documentId,
      requestBody: {
        requests: [
          {
            insertText: {
              location: { index: 1 },
              text: content,
            },
          },
        ],
      },
    });
    return { message: `Content written to document with ID ${documentId}` ,
    url:`https://docs.google.com/document/d/${documentId}/edit`};
  },
}


export const createGoogleDocTool={
  name: "createGoogleDoc",
  id:"createGoogleDoc",
  description: "Creates a new Google Doc with a given title.",
  parameters: {
    type: "object",
    properties: {
      title: { type: "string", description: "Title of the new document" },
    },
    required: ["title"],
  },
  async execute({ title }: { title: string}) {
    const auth = await getGoogleAuth();
    const docs = google.docs({ version: "v1", auth });
    const res = await docs.documents.create({
      requestBody: { title },
    });
    return { documentId: res.data.documentId, url: `https://docs.google.com/document/d/${res.data.documentId}/edit` };
  },
};