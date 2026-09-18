"""
Level 3: Web Search Agent with Tools (Strands Agents SDK)
=============================================================

Goal (see ../../sample_problem.md): LLMs can't observe the real world by
default - they only know what they were trained on, up to a cutoff date. To
answer questions about current events, an agent needs a TOOL that can fetch
live information from the internet. This level makes our agent behave like a
lightweight Perplexity clone:

    User: What is the latest on US tariffs?
    AI:   (fetches search results, reads them, answers based on that content)

What is a "tool" in Strands?
--------------------------------
A tool is just a (typically Python) function the LLM is allowed to call
mid-conversation. Strands runs an "agent loop": on each turn, the model can
either respond directly, or ask Strands to call one of the tools you gave
it, look at the tool's result, and then decide again (respond, or call
another tool) - all automatically, with no extra code from us.

Docs: https://strandsagents.com/docs/user-guide/concepts/tools/tools_overview/

Where does the search tool come from? (MCP)
-------------------------------------------------
Two earlier versions of this example tried, in order:
1. The generic `http_request` tool, pointed at a DuckDuckGo search page -
   unreliable, since scraping a search-results page can get flagged as bot
   traffic and returns a CAPTCHA instead of results.
2. The pre-built `tavily_search` tool from `strands-agents-tools` - this
   avoided the CAPTCHA problem, but that tool is now DEPRECATED in favor of
   Tavily's own official MCP server (warnings become hard errors in
   strands-agents-tools v0.9.0).

MCP (Model Context Protocol) is a standard way for an agent to connect to a
remote server that exposes tools, instead of installing those tools as a
Python package. Strands has built-in support for this via `MCPClient`: point
it at a server URL, and it hands back ready-to-use Strands tools - here,
Tavily's own hosted search tool, always kept up to date by Tavily.
Docs: https://strandsagents.com/docs/user-guide/concepts/tools/mcp-tools/
      https://docs.tavily.com/documentation/mcp
"""

import os
import sys

import boto3
from dotenv import load_dotenv

from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.tools.mcp.mcp_client import MCPClient

# Load TAVILY_API_KEY (and anything else) from a local .env file, if present.
load_dotenv()

# Tavily's remote, hosted MCP server - no local process to run, no separate
# "strands-agents-tools" install needed for this tool anymore.
TAVILY_MCP_URL = "https://mcp.tavily.com/mcp/"


def _nova_pro_model_id() -> str:
    """
    Amazon Nova Pro isn't invoked by a single global model ID - it's only
    offered through "cross-region inference profiles", which are scoped to
    a geography ("us.", "eu.", "apac.") rather than one specific region.
    Using the wrong geography prefix for your AWS region raises:
        ValidationException: The provided model identifier is invalid.
    So instead of hardcoding e.g. "us.amazon.nova-pro-v1:0", pick the prefix
    that matches whichever region boto3 actually resolves for you.

    We deliberately use `boto3.session.Session().region_name` here (NOT just
    `os.environ["AWS_REGION"]`) because boto3's own resolution also checks
    `~/.aws/config` (default region / AWS_PROFILE), which is how most people
    actually set their region - an env-var-only check would silently miss
    that and fall back to the wrong geography.
    Docs: https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference-support.html
    """
    region = boto3.session.Session().region_name or "us-east-1"
    if region.startswith("eu-"):
        geography = "eu"
    elif region.startswith("ap-"):
        geography = "apac"
    else:
        geography = "us"
    return f"{geography}.amazon.nova-pro-v1:0"


def build_mcp_client() -> MCPClient:
    """
    Create an MCPClient pointed at Tavily's official, hosted MCP server.

    We authenticate with an `Authorization: Bearer <key>` HEADER rather than
    putting the key in the URL as a query parameter (Tavily's docs support
    both). A header keeps the raw key out of URLs that might otherwise end
    up in logs, browser history, or error messages.
    """
    tavily_api_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_api_key:
        sys.exit(
            "Missing TAVILY_API_KEY. Copy .env.example to .env and add your "
            "free key from https://app.tavily.com/, then re-run this script."
        )

    return MCPClient(
        url=TAVILY_MCP_URL,
        headers={"Authorization": f"Bearer {tavily_api_key}"},
    )


def build_agent(tools: list) -> Agent:
    """
    Create the Level 3 agent: same conversational memory setup as Level 2,
    but now equipped with whatever tools Tavily's MCP server exposes
    (`tavily-search`, `tavily-extract`, etc.) - passed in from `main()`.
    """
    conversation_manager = SlidingWindowConversationManager(window_size=20)

    return Agent(
        # The system prompt is where we teach the agent WHEN to reach for
        # its tool - the search tool itself just returns raw results, it has
        # no opinion on how to use them in an answer.
        system_prompt=(
            "You are a research assistant that behaves like a lightweight "
            "Perplexity. When the user asks about something current, recent, "
            "or that you might not know (news, prices, releases, people, "
            "etc.), use the Tavily search tool with a concise search query "
            "before answering.\n"
            "Read the returned results, pick out the relevant snippets, and "
            "synthesize a direct answer in your own words - never just paste "
            "the raw search results back at the user. Briefly mention which "
            "source(s) the information came from (the result URLs).\n"
            "If the question is general knowledge that doesn't need current "
            "info, just answer directly without using the tool."
        ),
        # `tools` here are MCP-backed tool objects that MCPClient handed us -
        # from the agent's point of view they work exactly like any other
        # Strands tool.
        tools=tools,
        conversation_manager=conversation_manager,
        # Explicitly pinned to Amazon Nova Pro (via its cross-region inference
        # profile, resolved for your region above) instead of Strands'
        # Anthropic-model default, so this example doesn't compete for a
        # shared Bedrock Anthropic usage quota. Nova Pro supports tool use,
        # which this level relies on for the Tavily search tool. Swap the
        # "-pro-" for "-lite-" in _nova_pro_model_id() for a cheaper/faster
        # (but less capable) alternative.
        model=_nova_pro_model_id(),
    )


def main() -> None:
    """
    CLI loop, structurally similar to Level 2 (same agent reused across
    turns for memory), with one extra wrinkle: the MCP connection to Tavily
    is only "live" for as long as we're inside the `with mcp_client:` block,
    so the agent has to be built (and the whole chat loop run) inside it.
    """
    print("=" * 60)
    print("Strands Level 3: Web Search Agent (MCP tools + memory)")
    print("Try: 'What is the latest on US tariffs?'")
    print("Type 'quit' or 'exit' to stop.")
    print("=" * 60)

    mcp_client = build_mcp_client()

    # Entering this `with` block opens the connection to Tavily's MCP server;
    # leaving it (including via an exception) cleanly closes it again.
    with mcp_client:
        # Ask the MCP server what tools it offers, and hand them straight to
        # the agent - no manual wiring of individual tool functions needed.
        tools = mcp_client.list_tools_sync()
        agent = build_agent(tools)

        while True:
            try:
                user_question = input("\nYour question: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye!")
                break

            if not user_question:
                continue
            if user_question.lower() in ("quit", "exit"):
                print("Goodbye!")
                break

            print("\nThinking (may fetch search results)...\n")
            # Strands will automatically:
            #   1. Ask the model what to do next.
            #   2. If the model wants to call a Tavily tool, Strands makes an
            #      MCP call to Tavily's server and feeds the result back.
            #   3. Repeat until the model produces a final text answer.
            # All of that happens inside this single call.
            agent(user_question)


if __name__ == "__main__":
    main()
