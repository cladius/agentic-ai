# Level 2: Conversational Memory Agent (Strands)

## Overview

Builds on [Level 1](../Level1/README.md) by giving the agent memory of the
current conversation, so it can answer follow-up questions using earlier
context - matching the Level 2 goal in
[`sample_problem.md`](../../sample_problem.md):

```
User: My name is Sakhi, and I am an engineering student interested in
      compiler design and ML. What are some good career options?
AI:   (some answer from LLM)
User: What are some relevant textbooks that align with my interests?
AI:   (based on prior info....)
```

## How memory works in Strands

A `strands.Agent` keeps its own transcript in `agent.messages`. Reuse the
**same** `Agent` object across multiple calls and Strands automatically
sends the accumulated history back to the model each time - no manual chat
history list needed. That's the whole trick: Level 1 created a new `Agent`
every question (no memory); Level 2 creates **one** `Agent` for the whole
session (memory).

To stop that history from growing forever, we attach a
[`SlidingWindowConversationManager`](https://strandsagents.com/docs/user-guide/concepts/agents/conversation-management/),
which keeps only the most recent N messages and drops older ones.

## Requirements

- Python 3.10+
- AWS credentials with Bedrock model access (see
  [Strands quickstart](https://strandsagents.com/docs/user-guide/quickstart/python/)).
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

## Run it

```bash
python agent.py
```

Try the sample interaction above: tell the agent your name and interests,
then ask a follow-up question that relies on what you just said. When you
type `quit`/`exit`, the script prints the full transcript Strands kept in
`agent.messages` so you can see exactly what memory it was working with.

## How it works

- `build_agent()` returns one `Agent`, configured with a
  `SlidingWindowConversationManager(window_size=20)`.
- `main()` creates that agent **once**, outside the input loop, and reuses
  it for every message - this is the only structural difference from
  Level 1's `agent.py`.
- After the loop ends, we print `agent.messages` to make the accumulated
  memory visible.

Read `agent.py` for line-by-line comments.

## Next steps

- [Level 3](../Level3/README.md) adds a real tool (web search) from the
  `strands-agents-tools` package so the agent can look things up instead of
  relying only on what it already "knows".
