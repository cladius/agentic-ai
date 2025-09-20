# Goal

A simple demonstration using Python + Langflow to showcase how we can combine traditional programming with GenAI to provide a better user experience.

## Langflow Changes

Modify the prompt to ensure Structured Ouput is returned which can be programmatically parsed by the Python code [quiz.py](https://github.com/cladius/agentic-ai/blob/master/langflow/Misc/quiz_cli/quiz.py)

```
{context}

---

Given the context above, generate a MCQ quiz with 10 questions and 4 options for each question. The questions should be about the topic {question} There should be exactly one correct answer for each question. Provide the answer key at the bottom.

Send this as a JSON schema. Return only the JSON schema. The JSON schema should be made up of an array of objects. Each object should have the following fields - question, options (as an Array) and correct_answer (as an integer from 0 to 3).
```

Generate the Langflow API key via the steps mentioned [here](https://docs.langflow.org/api-keys-and-authentication#create-a-langflow-api-key).

Run the actual curl command for the workflow via Workflow > Share > API Access > cURL

## Claude.AI Prompt

You can create a simple Python application to invoke the Langflow API and provide a cli-based quiz experience for the user OR use [Claude](https://claude.ai) to generate it for you.

<details>
  <summary><b>Sample Prompt</b></summary>
what's the easiest way to have a CLI python appn that will invoke my langflow api endpoint running locally to create a 10 question MCQ and give me a score. 

The curl request is curl --request POST \
     --url 'http://localhost:7860/api/v1/run/973c0769-772b-4036-9c9f-29bb272ea4f3?stream=false' \
     --header 'Content-Type: application/json' \
     --header "x-api-key: $LANGFLOW_API_KEY" \
     --data '{
                   "output_type": "chat",
                   "input_type": "chat",
                   "input_value": "RAG"
         }'

The truncated response is 

{"session_id":"973c0769-772b-4036-9c9f-29bb272ea4f3","outputs":[{"inputs":{"input_value":"RAG"},"outputs":[{"results":{"message":{"text_key":"text","data":{"timestamp":"2025-09-15 15:32:52 UTC","sender":"Machine","sender_name":"AI","session_id":"973c0769-772b-4036-9c9f-29bb272ea4f3","text":"json\n[\n  {\n    \"question\": \"What does RAG stand for in the context of AI?\",\n    \"options\": [\n      \"Retrieval Augmented Generation\",\n      \"Random Access Grid\",\n      \"Recursive Algorithmic Graph\",\n      \"Reinforcement Adaptive Guidance\"\n    ],\n    \"correct_answer\": 0\n  },\n  {\n    \"question\": \"Which component of RAG is responsible for fetching relevant documents?\",\n    \"options\": [\n      \"Retriever\",\n      \"Generator\",\n      \"Tokenizer\",\n      \"Decoder\"\n    ],\n    \"correct_answer\": 0\n  },\n  {\n    \"question\": \"In a typical RAG pipeline, after retrieval, what is the next step?\",\n    \"options\": [\n      \"Generate a response using the retrieved context\",\n      \"Store the documents in a database\",\n      \"Compress the retrieved text\",\n      \"Validate the user query\"\n    ],\n    \"correct_answer\": 0\n  },\n  {\n    \"question\": \"Why is the 'G' (generation) step necessary in RAG?\",\n    \"options\": [\n      \"To synthesize a coherent answer from retrieved snippets\",\n      \"To generate new documents for the knowledge base\",\n      \"To generate embeddings for retrieval\",\n      \"To generate a summary of the entire corpus\"\n    ],\n    \"correct_answer\": 0\n  },\n  {\n    \"question\": \"Which of the following is NOT typically part of a RAG system?\",\n    \"options\": [\n      \"Embedding model\",\n      \"Indexing engine\",\n      \"Speech-to-text converter\",\n      \"Language model for generation\"\n    ],\n    \"correct_answer\": 2\n  },\n  {\n    \"question\": \"What is the main advantage of using RAG over a pure generative model?\",\n    \"options\": [\n      \"It can incorporate up-to-date external knowledge\",\n      \"It requires no training data\",\n      \"It runs faster on GPUs\",\n      \"It eliminates the need for tokenization\"\n    ],\n    \"correct_answer\": 0\n  },\n  {\n    \"question\": \"Which type of data source is commonly used with the retriever in RAG?\",\n    \"options\": [\n      \"Structured databases\",\n      \"Unstructured text documents\",\n      \"Audio recordings\",\n      \"Image datasets\"\n    ],\n    \"correct_answer\": 1\n  },\n  {\n    \"question\": \"In RAG, what is the role of embeddings?\",\n    \"options\": [\n      \"To represent documents and queries in a vector space for similarity search\",\n      \"To encode the output text into binary format\",\n      \"To compress the retrieved documents\",\n      \"To generate the final answer directly\"\n    ],\n    \"correct_answer\": 0\n  },\n  {\n    \"question\": \"Which of the following is a common retrieval technique used in RAG?\",\n    \"options\": [\n      \"FAISS\",\n      \"BERT embeddings\",\n      \"TF-IDF\",\n      \"All of the above\"\n    ],\n    \"correct_answer\": 3\n  },\n  {\n    \"question\": \"What does the term 'augmented' refer to in Retrieval Augmented Generation?\",\n    \"options\": [\n      \"The model is enhanced with external knowledge\",\n      \"The model uses augmented reality for visualization\",\n      \"The model is trained on augmented datasets\",\n      \"The model generates augmented text\"\n    ],\n    \"correct_answer\": 0\n  }\n]\n","files":[],"error":false,"edit":false,"properties":{"text_color":"","background_color":"","edited":false,"source":{"id":"GroqModel-thtm5","display_name":"Groq","source":"openai/gpt-oss-20b"},"icon":"Groq","allow_markdown":false,"positive_feedback":null,"state":"complete","targets":[]},"category":"message","content_blocks":[],"id":"063af91e-1051-4c0c-bf05-81c2bb1dcd5a","flow_id":"973c0769-772b-4036-9c9f-29bb272ea4f3","duration":null},"default_value":"","text":"```json\n[\n  {\n    \"question\": \"What does RAG stand for in the context of AI?\",\n    \"options\": [\n      \"Retrieval Augmented Generation\",\n      \"Random Access Grid\",\n      \"Recursive Algorithmic Graph\",\n      \"Reinforcement Adaptive Guidance\"\n    ],\n    \"correct_answer\": 0\n  },\n  {\n    \"question\": \"Which component of RAG is responsible for fetching relevant documents?\",\n    \"options\": [\n      \"Retriever\",\n      \"Generator\",\n      \"Tokenizer\",\n      \"Decoder\"\n    ],\n    \"correct_answer\": 0\n  },\n  {\n    \"question\": \"In a typical RAG pipeline, after retrieval, what is the next step?\",\n    \"options\": [\n      \"Generate a response using the retrieved context\",\n      \"Store the documents in a database\",\n      \"Compress the retrieved text\",\n      \"Validate the user query\"\n    ],\n    \"correct_answer\": 0\n  },\n  {\n    \"question\": \"Why is the 'G' (generation) step necessary in RAG?\",\n    \"options\": [\n      \"To synthesize a coherent answer from retrieved snippets\",\n      \"To generate new documents for the knowledge base\",\n      \"To generate embeddings for retrieval\",\n      \"To generate a summary of the entire corpus\"\n    ],\n    \"correct_answer\": 0\n  },\n  {\n    \"question\": \"Which of the following is NOT typically part of a RAG system?\",\n    \"options\": [\n      \"Embedding model\",\n      \"Indexing engine\",\n      \"Speech-to-text converter\",\n      \"Language model for generation\"\n    ],\n    \"correct_answer\": 2\n  },
</details>

## Sample Output

```
python quiz.py
📚 Enter the topic for your quiz: memory
🎯 MCQ Quiz Generator
==================================================
🔄 Generating questions about 'memory'...

🚀 Starting quiz on 'memory' with 10 questions!
   (Press Ctrl+C to exit at any time)

📝 Question 1/10:
   Which type of memory is described as the ability to recall recent conversational context within a single interaction?

   A. Long-term memory
   B. Semantic memory
   C. Short-term memory
   D. Procedural memory

   Your answer (A/B/C/D): C
   ✅ Correct!

📝 Question 2/10:
   In the context of agentic applications, what is the primary purpose of storing user attributes in long-term memory?

   A. To increase computational speed
   B. To enable proactive recall during related queries
   C. To reduce storage costs
   D. To anonymize user data

   Your answer (A/B/C/D): B
   ✅ Correct!

```
