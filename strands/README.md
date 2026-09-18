# Strands Agents Exploration

Hands-on examples built with [Strands Agents](https://strandsagents.com/), AWS's
open-source SDK for building agents in a model-driven way.

> Want to understand the concepts behind each level? See the
> [sample problem](../sample_problem.md).

## Levels

- [**Level 1: Hello World Agent**](Level1/README.md) - a single agent, no
  tools, no memory.
- [**Level 2: Conversational Memory Agent**](Level2/README.md) - the agent
  remembers earlier turns in the conversation.
- [**Level 3: Web Search Agent with Tools**](Level3/README.md) - connects to
  Tavily's official MCP server so the agent can look up current information
  on the web.

Levels 1-3 are deliberately minimal and heavily commented, meant to be read
top to bottom in `agent.py`.

## Other examples

- [`marketing-assistant/`](marketing-assistant/) - a more advanced, custom-tool
  example (PDF ingestion -> content analysis -> social post generation) built
  with Strands and AWS Bedrock, not part of the 5-level progression.

## Requirements common to all examples

- Python 3.10+
- AWS credentials with access to a Bedrock model (Strands defaults to Amazon
  Bedrock). Run `aws configure`, or set `AWS_ACCESS_KEY_ID` /
  `AWS_SECRET_ACCESS_KEY` / `AWS_REGION` in your environment. See the
  [Strands quickstart](https://strandsagents.com/docs/user-guide/quickstart/python/).
- Per-level dependencies via `pip install -r requirements.txt` inside that
  level's folder.

## Resources

- [Strands Agents documentation](https://strandsagents.com/docs/)
- [strands-agents-tools (pre-built tools package)](https://github.com/strands-agents/tools)
