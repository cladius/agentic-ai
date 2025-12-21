
# **LEVEL 4**
 **OBJECTIVE**\
 Create a vector store (e.g., Compiler Design book) and push content into it

 Vectorize a resume and extract structured info

 Design sequential or parallel agent workflows

 Enable agent-to-tool calling
 # **Vector Stores**
 During level 4 we brushed over the importance of recall power and context. The context window that an agent is endowed with is usually considered to be minimal in size and restricted to textual input from the user. \
 This makes agentic solutions entirely useless for individuals working in academia or other content intensive fields. Here, the need for larger context, from document sources, arises. 

    A vector store consists of a database that 'embeds' vectorized 'chunks' of documents in tables. 
 Whenever a query is made in context to uploaded documents, a search tool is used to return the top K most relevant embeddings from the vector store. These embeddings are taken into context when answering the query.

    NOTE: Mastra is constantly undergoing version upgradation and new features are regularly added. Make sure to look out for updates.

 Mastra's playground now comes with the built-in ability to upload multiple documents and chunking + vectorizing of documents. This feature rolled out while I was working on a tool of my own for the same, rendering it unnecessary. 
 ## Vector Query Tool
 The query tool uses Google's `text-embedding-004` model to search for the top K embeddings from the vector store and return the results. If no results are found 'Search failed' is returned. 
***
### **Challenges**
- The vector query tool was relatively simple to implement. The problem laid with the embedding tool that I was creating, which in the end was not needed.
- Since Mastra's playground could not be changed, I made a separate frontend solely for uploading documents. Connecting the Mastra server, frontend and the backend for the uploads proved to be a bit of a challenge.

### Output screenshot
![Output photo](https://github.com/meghnamankotia/mastra-psl/blob/main/assets/Screenshot%202025-11-29%20154157.png)
