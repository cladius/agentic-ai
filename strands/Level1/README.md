# Level 1: Hello World Agent (Strands)

## Overview

The simplest possible agent: one `Agent`, powered by an LLM, with **no tools**
and **no memory**. Every question is answered in complete isolation - the
agent has no idea what you asked it before.

This mirrors the Level 1 goal in [`sample_problem.md`](../../sample_problem.md):

```
User: What are the principles of OOPS?
AI: (whatever answer we get from LLM)
```

## What is Strands?

[Strands Agents](https://strandsagents.com/) is AWS's open-source SDK for
building agents. You describe an `Agent` (its system prompt, tools, memory
config) and the SDK runs the "agent loop" - deciding, on each turn, whether
the LLM should just respond or call a tool. Level 1 has no tools, so the loop
is as simple as it gets: ask -> answer.

By default, Strands calls Amazon Bedrock models (e.g. Anthropic Claude), so
you need AWS credentials configured locally.

## Requirements

- Python 3.10+
- AWS credentials with access to a Bedrock model (run `aws configure` if you
  haven't already, or export `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` /
  `AWS_REGION`). See [Strands quickstart](https://strandsagents.com/docs/user-guide/quickstart/python/).
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

## Run it

```bash
python agent.py
```

Ask a question (e.g. `What are the principles of OOPS?`), read the answer,
then ask a follow-up like `What did I just ask you?` - the agent will have no
idea, because Level 1 intentionally has no memory. Type `quit` or `exit` to
stop.

## How it works

- `build_agent()` creates a `strands.Agent` with only a `system_prompt` - no
  `tools=`, no `conversation_manager=`/`session_manager=`.
- The CLI loop in `main()` calls `build_agent()` again on **every** question,
  so no conversation history ever carries over between turns.
- `agent(user_question)` runs the agent loop for that one message and prints
  the response.

Read `agent.py` for line-by-line comments explaining each piece.

## Next steps

- [Level 2](../Level2/README.md) adds conversation memory so the agent
  remembers earlier turns.
- [Level 3](../Level3/README.md) adds a tool from the `strands-agents-tools`
  package so the agent can search the web.
