# Bedrock Agents Repository

This repository contains a collection of Bedrock agents designed to solve complex problems using an iterative approach. Each level introduces new capabilities, building upon the previous levels to create increasingly sophisticated agentic solutions. This approach is ideal for training individuals with no prior knowledge of Generative AI (GenAI) to gain familiarity and confidence in agentic frameworks.

## What are Bedrock Agents?

Bedrock agents are AI-driven systems built on Amazon Bedrock, designed to perform specific tasks by leveraging foundational models, memory, and tools. These agents can be customized to solve a wide range of problems, from simple question-answering to complex multi-agent workflows.

### Key components used to implement these levels

1. **Memory**:
   - Memory enables agents to retain context across interactions, making them capable of providing context-aware responses.
   - Example: Conversational memory allows agents to remember user preferences or prior queries.

2. **Prompt**:
   - Prompts define the behavior and instructions for the agent.
   - Example: "You are a helpful assistant. Your task is to answer the user's questions clearly and concisely."

3. **Action Groups**:
   - Action groups define a sequence of actions or tools that the agent can use to perform tasks.
   - Example: A web search action group integrates APIs like Tavily Search to fetch real-time information.

4. **Foundational Models**:
   - These are pre-trained models provided by Amazon Bedrock, such as Amazon Titan or Amazon Nova, used for tasks like text generation, embedding, or summarization.

5. **Knowledge Bases**:
   - Knowledge bases store proprietary information in a vectorized format, enabling agents to perform Retrieval Augmented Generation (RAG).
   - Example: A resume ingested into a knowledge base allows the agent to answer questions about the user's qualifications.

6. **Flows**:
   - Flows define the orchestration of multi-agent and multi-tool systems.
   - Example: A flow for the NotebookLM Clone agent might include steps for ingesting files, generating mind maps, and creating podcasts.
   
7. **Lambda Functions**
   - Lambda functions are used to extend the capabilities of Bedrock agents by integrating external tools and APIs. 
   - These functions are essential for enabling agents to interact with the real world and perform tasks beyond the capabilities of foundational models.

### Problem Statement Overview
* Refer to the [sample problem](https://github.com/cladius/agentic-ai/blob/master/sample_problem.md) to understand the 5 level problem.


## Export agents, Save agents to JSON & Create agents Using CLI and AWS SDK
Before starting, ensure:
- AWS CLI installed
- AWS credentials configured (`aws configure`)
- IAM role created for Bedrock Agents
- Proper permissions for:
  - `bedrock-agent:*`
  - `bedrock-agent-runtime:*`

Verify CLI:

```bash
aws --version
```

### Export Existing Agent to JSON

Retrieve the existing agent configuration:

```bash
aws bedrock-agent get-agent \
  --agent-id <YOUR_AGENT_ID> \
  --region us-east-1 > original_agent.json
```

This exports the full agent definition.

### You have to clean the JSON for Reuse

Open 'original_agent.json' and remove:
Remove These Fields as they are created at the time of agent creation

- `agentId`
- `agentArn`
- `agentStatus`
- `createdAt`
- `updatedAt`
- `preparedAt`
- `clientToken`
- Outer `"agent": {}` wrapper
- Any other read-only fields


Final Clean JSON Example

Save this as:

```
create_agent_payload.json
```

Example structure:

```json
{
  "agentName": "my-new-agent",
  "instruction": "You are a helpful assistant who answers all user queries.",
  "foundationModel": "anthropic.claude-3-5-sonnet-20240620-v1:0",
  "agentResourceRoleArn": "arn:aws:iam::<account-id>:role/service-role/AmazonBedrockExecutionRoleForAgents",
  "orchestrationType": "DEFAULT"
}
```



### Create Agent Using AWS CLI

```bash
aws bedrock-agent create-agent \
  --cli-input-json file://create_agent_payload.json \
  --region us-east-1
```

If successful, you will receive:

```json
{
  "agent": {
    "agentId": "NEW_AGENT_ID",
    "agentName": "my-new-agent",
    "agentStatus": "CREATING"
  }
}
```

Save the returned `agentId`.

Check Agent Status

```bash
aws bedrock-agent get-agent \
  --agent-id <NEW_AGENT_ID> \
  --region us-east-1
```

Wait until:

```
"agentStatus": "PREPARED"
```

The agent must be `PREPARED` before invocation.



### (Recommended) Create Agent Alias

Creating an alias allows version control and easier updates.

```bash
aws bedrock-agent create-agent-alias \
  --agent-alias-name prod \
  --agent-id <NEW_AGENT_ID> \
  --region us-east-1
```

Response will include:

```json
{
  "agentAlias": {
    "agentAliasId": "ALIAS_ID"
  }
}
```



### Create Agent Using AWS SDK (Python)

Install boto3

```bash
pip install boto3
```

Python Script (`create_agent.py`)

```python
import json
import boto3

# Load cleaned JSON
with open("create_agent_payload.json") as f:
    agent_payload = json.load(f)

client = boto3.client("bedrock-agent", region_name="us-east-1")

response = client.create_agent(**agent_payload)

print("Agent Created Successfully!")
print("Agent ID:", response["agent"]["agentId"])
```

Run:

```bash
python create_agent.py
```

Invoke Agent Using SDK (Python)

```python
import boto3

runtime = boto3.client("bedrock-agent-runtime", region_name="us-east-1")

response = runtime.invoke_agent(
    agentId="NEW_AGENT_ID",
    sessionId="session1",
    inputText="Hello, how are you?"
)

print(response)
```
## References

- For detailed descriptions of each level, visit the [Agentic AI Sample Problem](http://github.com/cladius/agentic-ai/blob/master/sample_problem.md).
- For more examples and advanced use cases, visit the [Amazon Bedrock Agent Samples](https://github.com/awslabs/amazon-bedrock-agent-samples).




