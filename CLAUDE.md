# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A learning/reference repo for **Agentic AI**, organized by framework. Each framework directory contains the *same 5-level progressive problem* (see `sample_problem.md`) solved independently in that framework, so people can compare approaches across LangGraph, Agno, Pydantic AI, LangChain, LangChain4j, Google ADK, MCP, Langflow, AWS Bedrock Agents, and Strands.

The 5 levels are always:
1. **Basic** — single agent, no tools, no memory.
2. **Conversational Memory** — add state/memory across turns.
3. **Tools** — add web search so the agent behaves like a lightweight Perplexity.
4. **Vector Store / RAG** — ingest a document (e.g. a resume) into a vector store and answer questions from it.
5. **NotebookLM mimic** — multi-agent, multi-tool system: ingest files/YouTube/web pages, answer questions, generate a mind map, and produce a 2-person audio podcast.

There is no single build/test/lint pipeline across the repo — each framework folder (and often each `Level*` subfolder within it) is a **self-contained example** with its own dependencies, README, and run instructions. Treat each `LevelN` directory as an independent mini-project.

## Repository layout

- `adk/` — Google Agent Development Kit (Python + Gemini). `levelN/agent.py` per level; level 4 adds Vertex AI RAG (`rag.py`), level 5 is a multimodal CLI (`agent_setup.py`, `multimodal_interface.py`).
- `agno/` — Agno framework (Python). Note capitalized `Level1`..`Level5` dirs (inconsistent casing vs. other frameworks), plus `Eval/` and `Observability/` (Langfuse tracing) extras.
- `Bedrock-Agents/` — AWS Bedrock Agents, defined mostly as exported/importable agent JSON (`*.json`) plus Lambda action-group code and an `Extra_Connect_With_AstraDB/` bonus example. Uses AWS CLI/boto3, not a typical Python app you `run`.
- `langchain/` — a single introductory LangChain + Groq terminal chat example (not split into levels); `config.py` holds config, `.env` supplies API keys.
- `langchain4j/` — Java/Maven modules, one per level (`Level1`..`level4` note inconsistent casing, `Level5`, plus a `practise` module). Each has its own `pom.xml`.
- `langflow/` — visual flows exported as JSON (`*.json` flow definitions) rather than code; each `LevelN/README.md` documents the flow's components. `Misc/` has extra flows not part of the level progression.
- `langgraph/` — Python + LangGraph, managed with `uv` (has `pyproject.toml`/`uv.lock` at the `langgraph/` root). This is the most "project-like" folder — see below.
- `mcp/` — a standalone Model Context Protocol server example (`fastmcp`, streamable HTTP), managed with `uv`.
- `pydantic/` — Pydantic AI (Python + Gemini), one dir per level.
- `strands/` — AWS Strands Agents SDK. `Level1`-`Level3` follow the standard progression (hello-world, conversational memory, web search via Tavily's official MCP server through Strands' `MCPClient`); `marketing-assistant/` is a separate, more advanced custom-tool example not part of the 5-level series.
- `design-aids/` — methodology doc, not code: how to write a `Interaction.md` (user/system interaction) and `AgentSpec.md` (agent roles/responsibilities/tools) *before* implementing an agentic system.
- `sample_problem.md` — canonical definition of the 5 levels; read this before implementing/reviewing a level in any framework.

## Running examples

There is no repo-wide install step. Per-framework patterns:

**Python frameworks with `requirements.txt` per level** (`adk/`, `agno/`, `pydantic/`, most of `langgraph/`):
```bash
cd <framework>/<LevelN>
python -m venv venv && source venv/bin/activate   # or use uv
pip install -r requirements.txt
cp .env.example .env   # fill in API keys, when present
python <entrypoint>.py
```

**`langgraph/`** uses `uv` at the top level instead of per-level venvs:
```bash
cd langgraph
uv sync                 # creates/updates the environment from pyproject.toml
cd Level3
python tool_as_node.py  # see the level's README for the exact entrypoint
```
`langgraph/Level3/langgraph.json` and `langgraph/Level5/langgraph.json` configure those levels for the LangGraph CLI/Studio.

**`mcp/`** also uses `uv`:
```bash
cd mcp
uv sync
python mcp_streamable_http.py
```

**`langchain4j/`** (Maven/Java):
```bash
cd langchain4j/Level1
mvn compile exec:java   # or use the run command in that level's README
```

**`Bedrock-Agents/`** — no local runtime; agents are created/managed via AWS CLI (`aws bedrock-agent create-agent ...`) or boto3 scripts, using the checked-in JSON payloads as agent definitions. Requires `aws configure` and an IAM role with `bedrock-agent:*` / `bedrock-agent-runtime:*` permissions.

**`langflow/`** — flows are imported into a running Langflow instance via its UI/playground, not executed as scripts.

Always check the specific `LevelN/README.md` (or framework root README) before running — entrypoint filenames and required env vars vary per level and are documented there, not here.

## Conventions across the repo

- Secrets (Google/Gemini, Tavily, ElevenLabs, Groq, LangSmith, AWS, etc.) are supplied via a `.env` file local to each project folder — never hardcoded. Many levels ship a `.env.example` to copy from.
- Each level folder's README documents that level's specific setup, API keys needed, and how to run it — treat it as the source of truth over any repo-wide assumption.
- Directory casing for level folders is inconsistent between and even within frameworks (`Level1` vs `level4`, `Level1` vs `l1-config.py`) — match the existing casing exactly when referencing or adding paths.
- When adding a new framework or level, follow the existing pattern: mirror the 5-level structure from `sample_problem.md`, include a README describing setup/run steps, and keep the example self-contained within its own directory.
