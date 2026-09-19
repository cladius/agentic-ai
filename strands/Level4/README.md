# Level 4: Vector Store / RAG Agent (Strands)

## Overview

Builds on [Level 3](../Level3/README.md) by giving the agent access to
**proprietary content** instead of only the open web, matching the Level 4
goal in [`sample_problem.md`](../../sample_problem.md):

```
User: (a question about whatever's in your knowledge base)
AI:   (answers based on the ingested content, e.g. a resume - "What is my AIR? What is my CGPA?")
```

## Where the ingestion happened

Unlike the other frameworks' Level 4 in this repo, this example doesn't
build or populate its own vector store in code. It connects to an AWS
**Bedrock managed Knowledge Base** that's already been created and
populated - e.g. documents uploaded to the knowledge base's S3 data
source and synced (ingested) via the [Bedrock
console](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
or `aws bedrock-agent` CLI - *before* running this agent. Bedrock handles
chunking, embedding, and storage; `agent.py` here is retrieval-only.

## The tool: `MemoryManager` + `BedrockKnowledgeBaseStore`

The "obvious" tool for this, `retrieve` from `strands-agents-tools`, is
**deprecated** (the warning becomes a hard error in v0.9.0). Its own
deprecation message points at the replacement:

> "retrieve is deprecated. This warning becomes an error log in v0.9.0.
> Migration path: use MemoryManager with
> BedrockKnowledgeBaseStore(writable=False). Note the store applies no
> relevance-score floor, so filter results yourself."

Source: [`strands_tools/retrieve.py`](https://github.com/strands-agents/tools/blob/main/src/strands_tools/retrieve.py)

So this example uses that migration path: Strands' `MemoryManager` (docs:
[Memory overview](https://strandsagents.com/docs/user-guide/concepts/memory/overview/))
wired to a [`BedrockKnowledgeBaseStore`](https://strandsagents.com/docs/user-guide/concepts/memory/bedrock-knowledge-base/)
pointed at the KB ID from `.env`. `BedrockKnowledgeBaseStore` defaults
`writable` to `False`, so a store built with just a `knowledge_base_id` is
read-only out of the box - exactly what a lookup-only RAG agent needs.

Passing `memory_manager=MemoryManager(stores=[store])` to an `Agent` turns
on **two retrieval mechanisms at once**, by default, with zero extra
config:

1. A `search_memory` **tool** the model can call mid-conversation, exactly
   like the Tavily search tool in Level 3 - the model decides when it needs
   to look something up.
2. Automatic prompt **injection** - the top search results for the user's
   question are folded into the prompt before the model even runs, so it
   often already has relevant context without calling the tool at all.

Both are harmless to leave on together, which is what makes this the
simplest working setup. If that ever feels redundant, `injection=False` on
`MemoryManager` turns off #2 and leaves pure tool-call-driven retrieval,
matching Level 3's "the agent decides to reach for a tool" pattern - this
example doesn't do that, to keep things minimal.

## The model: Amazon Nova Pro

Same as [Level 3](../Level3/README.md#the-model-amazon-nova-pro): pinned to
Nova Pro via its cross-region inference profile (auto-resolved for your
region by `_nova_pro_model_id()`), since it supports tool use and keeps
this example off the shared Anthropic model quota in Bedrock.

## Requirements

- Python 3.10+
- AWS credentials with access to Amazon Nova Pro on Bedrock, **and** an
  IAM policy granting:
  - `bedrock:Retrieve` - performing the actual knowledge base search.
  - `bedrock:GetKnowledgeBase` - Strands calls this once, at agent
    construction, to auto-detect your KB's type (MANAGED/VECTOR/KENDRA/SQL).
    **If this permission is missing, you'll get an AccessDenied error that
    looks unrelated to search** - it happens before any question is asked.
  Scope both to your knowledge base's ARN.
- An existing, already-populated Bedrock managed Knowledge Base (see
  [Where the ingestion happened](#where-the-ingestion-happened) above).
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

## Setup

Create a `.env` file in this folder (copy `.env.example`) with your
knowledge base ID and region:

```env
KNOWLEDGE_BASE_ID=your_bedrock_knowledge_base_id
AWS_REGION=us-east-1
```

`AWS_REGION` matters here even if you already have a default region set
via `~/.aws/config`: `_nova_pro_model_id()` picks its cross-region
inference profile from whichever region boto3 resolves, and if your
Knowledge Base lives in a *different* region than that, lookups will fail
with a `ResourceNotFoundException` that doesn't obviously point at "wrong
region" as the cause.

## Run it

```bash
python agent.py
```

Ask something the ingested content should answer (e.g. `What is my CGPA?`
if the KB holds a resume). Ask a follow-up in the same session to confirm
conversational memory carries context across turns, like in Level 2/3.
Ask something the knowledge base doesn't cover and the agent should say so
rather than guess. Type `quit`/`exit` to stop.

## How it works

- `build_memory_manager()` builds a read-only `BedrockKnowledgeBaseStore`
  from `KNOWLEDGE_BASE_ID` and wraps it in a `MemoryManager`.
- `build_agent()` is otherwise the same shape as Level 2/3's: a
  `SlidingWindowConversationManager` for cross-turn memory, Nova Pro as the
  model, and now `memory_manager=...` instead of (or alongside) MCP tools.
- `main()` is simpler than Level 3's - no MCP connection to hold open, so
  no `with` block is needed.

Read `agent.py` for line-by-line comments on the memory wiring and the
agent loop.

## Where to go from here

- [Strands Memory concepts](https://strandsagents.com/docs/user-guide/concepts/memory/overview/) -
  `MemoryManager` also supports writable stores (`add_memory` tool) and
  conversation-based extraction, not used here since this level is
  read-only lookup.
- [Bedrock Knowledge Base Store docs](https://strandsagents.com/docs/user-guide/concepts/memory/bedrock-knowledge-base/) -
  covers `min_score`/`max_score` filtering (useful since, per the
  deprecated tool's own warning, the store applies no relevance-score
  floor by default) and other config knobs not used in this minimal
  example.
- Level 5 (multi-agent NotebookLM mimic) is the natural next step per
  [`sample_problem.md`](../../sample_problem.md), not yet implemented in
  this `strands/` folder.
