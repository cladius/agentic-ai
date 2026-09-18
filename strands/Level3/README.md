# Level 3: Web Search Agent with Tools (Strands)

## Overview

Builds on [Level 2](../Level2/README.md) by giving the agent a **tool**, so
it can look up current information on the web instead of only answering from
what the LLM already knows - matching the Level 3 goal in
[`sample_problem.md`](../../sample_problem.md):

```
User: What is the latest on US tariffs?
AI:   (performs the search, understands the content, then answers based on it)
```

## The tool: Tavily's official MCP server

This example connects to **Tavily's own hosted [MCP](https://modelcontextprotocol.io/)
server** (`https://mcp.tavily.com/mcp/`) using Strands' built-in `MCPClient`,
and hands whatever tools it exposes (a web search tool, etc.) straight to
the agent. MCP (Model Context Protocol) is a standard way for an agent to
use tools that live on a remote server, instead of installing them as a
Python package - Tavily maintains the server, so the tool stays up to date
without us pinning a package version.

This is actually the **third** iteration of this example, each one fixing a
real problem hit while building it:

1. First attempt: the generic `http_request` tool, pointed at a DuckDuckGo
   search-results page. Unreliable - scraping a search page like that gets
   flagged as bot traffic and returns a CAPTCHA instead of results.
2. Second attempt: the pre-built `tavily_search` tool from the
   `strands-agents-tools` package. Fixed the CAPTCHA problem (Tavily is a
   real search API, not something to scrape) - but that tool is itself
   **deprecated** in `strands-agents-tools` (warnings become hard errors in
   v0.9.0) in favor of...
3. This version: Tavily's **official MCP server**, which is what the
   deprecation warning itself points to. See
   [strands-agents/tools#604](https://github.com/strands-agents/tools/pull/604)
   and [Tavily's MCP docs](https://docs.tavily.com/documentation/mcp).

The agent decides *on its own*, based on the system prompt and the user's
question, whether it needs to search at all - e.g. "What is 2+2?" won't
trigger a search, but "What is the latest on US tariffs?" will.

## The model: Amazon Nova Pro

Unlike Levels 1-2 (which use Strands' default Bedrock model, an Anthropic
Claude model), this level explicitly pins the agent's `model` to Amazon Nova
Pro in `build_agent()`. Amazon Nova Pro supports tool use (needed for the
Tavily search tool) and keeps this example off the shared Anthropic model
quota in Bedrock.

Nova Pro is only invokable through a **cross-region inference profile**,
which is scoped to a geography (`us.`, `eu.`, `apac.`) rather than one
region - using the wrong prefix for your AWS region raises
`ValidationException: The provided model identifier is invalid.`
`_nova_pro_model_id()` in `agent.py` picks the right prefix automatically
from whichever AWS region `boto3` resolves for you (env vars, `AWS_PROFILE`,
or the `region` set in `~/.aws/config` - the same resolution order boto3
itself uses), so this works whether you're in `us-east-1`, `eu-west-1`,
`ap-south-1`, etc. Swap the `-pro-` for `-lite-` there for a cheaper/faster
model if Nova Pro is unavailable in your account/region.

## Requirements

- Python 3.10+
- AWS credentials with access to Amazon Nova Pro on Bedrock (see
  [Strands quickstart](https://strandsagents.com/docs/user-guide/quickstart/python/)
  for general setup; make sure Nova Pro is enabled for your account/region in
  the Bedrock console's "Model access" page).
- A free [Tavily API key](https://app.tavily.com/) for the MCP server.
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

## Setup

Create a `.env` file in this folder (copy `.env.example`) with your Tavily
key:

```env
TAVILY_API_KEY=your_tavily_api_key
```

## Run it

```bash
python agent.py
```

Ask something time-sensitive, e.g. `What is the latest on US tariffs?` or
`Who won the most recent Super Bowl?`, and watch the agent fetch and read
search results before answering. Ask something like `What is 12 * 8?` and
notice it just answers directly, without searching. Type `quit`/`exit` to
stop.

## How it works

- `build_mcp_client()` creates a Strands `MCPClient` pointed at Tavily's
  hosted MCP server URL, authenticating with an `Authorization: Bearer
  <key>` header (kept out of the URL, unlike Tavily's other documented
  option of a `?tavilyApiKey=...` query parameter).
- `main()` opens that connection with `with mcp_client:`, calls
  `mcp_client.list_tools_sync()` to get Strands-ready tool objects for
  whatever Tavily's server exposes, and passes them into `build_agent()` -
  everything else (the chat loop, memory) stays inside that `with` block,
  since the MCP connection is only live while it's open.
- `build_agent()` is otherwise the same as Level 2's, with the system prompt
  updated to explain *when* to search and how to turn results into an
  answer with sources.

Read `agent.py` for line-by-line comments on the MCP wiring and the agent
loop.

## Where to go from here

- [MCP tools in Strands](https://strandsagents.com/docs/user-guide/concepts/tools/mcp-tools/)
  - the same `MCPClient` pattern works for any MCP server, not just Tavily's.
- [`strands-agents-tools`](https://github.com/strands-agents/tools) ships
  other pre-built, non-deprecated tools (calculator, python REPL, file I/O,
  AWS calls, etc.) that can be added to `tools=[...]` the same way as a
  plain Python package, without MCP.
- Level 4 (vector store / RAG) and Level 5 (multi-agent NotebookLM mimic) are
  natural next steps per [`sample_problem.md`](../../sample_problem.md), not
  yet implemented in this `strands/` folder.
