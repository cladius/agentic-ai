# LEVEL 3

## Overview
This level aims to create an agent that is equipped with tools to assist users. The guidelines suggest creating a searching tool, however in this repo I've created a tool that introduces creation/writing features via Google Docs/Drive integration. 

## Some insight on tools

Tools are functions that make your agentic AI, agentic. Agents are able to carry out specific tasks beyond text generation. By making use of APIs and databases, agents can be provided with powerful tools. Tools can either be made from scratch or from MCP (Model Context Protocol) providers.

Model Context Protocol - MCP servers allow agents to access external tools using MCP Clients provided by Mastra. MCP is an open standard, this allows different frameworks irrespective of their base language or hosting.


## Create/ Write Google Doc tool
For this level I wanted to integrate tools that allowed creation and manipulation of Google Docs.

I created 2 custom tools  `createGoogleDocTool`  and  `writeGoogleDocTool`  in the  `tools/docs.ts`  file using the Google Docs and Drive APIs. Creation of documents is done using the docs.documents.create method and writing is done using batchUpdate method.
I also created a function to carry out the OAuth for accessing Google accounts.

### Set Up
- `CLIENT_ID`
- `CLIENT_SECRET`
- `REDIRECT_URI`
- `TOKEN_PATH`
have to be added to the  `.env`  file

Finally, ensure that you've added the required gmail ids to the scope of your project on the Google Cloud Platform. GCP only allows these ids to perform OAuth as the project is still within the testing phase.

## Problems Faced 
-   It was my first time working with Google's OAuth so the set up took a little time.
    
-   The Mastra documentation states that tools can be create by making instances of the createTool class (some sources mentioned defineTool), however this is not necessary as the tools can be exported as simple functions. This was not really a challenge, but rather a small discovery that is not properly documented.

## Output screenshots 
![Output image](https://github.com/meghnamankotia/mastra-psl/blob/main/assets/Screenshot%202025-11-29%20153934.png)




