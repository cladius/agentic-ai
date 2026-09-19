"""
Level 1: Hello World Agent (Strands Agents SDK)
=================================================

Goal (see ../../sample_problem.md): build the simplest possible agent -
a single agent, powered by an LLM, with NO tools and NO memory.

What is "Strands"?
-------------------
Strands Agents (https://strandsagents.com/) is an open-source SDK from AWS for
building agents in a "model-driven" way: you describe what the agent CAN do
(its tools, its system prompt) and the LLM itself decides what to do at each
step (this is often called the "agent loop"). For Level 1 we don't give the
agent any tools at all, so the loop is trivial: user asks -> LLM answers.

By default, Strands talks to Amazon Bedrock, so you need AWS credentials
available in your environment (e.g. via `aws configure`, or AWS_ACCESS_KEY_ID /
AWS_SECRET_ACCESS_KEY env vars) with access to a Bedrock model such as
Anthropic Claude. See: https://strandsagents.com/docs/user-guide/quickstart/python/
"""

import boto3

# `Agent` is the core building block of Strands - it wraps an LLM plus
# (optionally) a system prompt, tools, and memory/session configuration.
from strands import Agent


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


def build_agent() -> Agent:
    """
    Create and return a brand-new Strands Agent.

    Notice there are NO `tools=[...]` and NO `conversation_manager=` /
    `session_manager=` arguments here - that's what makes this a Level 1
    ("no tools, no memory") agent. The `system_prompt` just tells the LLM
    how to behave; it does not give it any new capabilities.
    """
    return Agent(
        # `system_prompt` shapes the persona/behaviour of the agent.
        # It is NOT a tool - the agent still can't do anything but talk.
        system_prompt=(
            "You are a friendly, concise AI tutor. Answer the user's question "
            "directly in a few sentences. If you don't know something, say so "
            "instead of guessing."
        ),
        # Explicitly pinned to Amazon Nova Pro (via its cross-region inference
        # profile, resolved for your region above) instead of Strands'
        # Anthropic-model default, so this example doesn't compete for a
        # shared Bedrock Anthropic usage quota. Swap the "-pro-" for "-lite-"
        # in _nova_pro_model_id() for a cheaper/faster (but less capable)
        # alternative.
        model=_nova_pro_model_id(),
    )


def main() -> None:
    """
    Simple CLI loop to chat with the Level 1 agent.

    IMPORTANT: to keep this a true "no memory" example, we create a FRESH
    Agent object on every single question (see the loop below). A Strands
    Agent normally accumulates conversation history in `agent.messages`
    across multiple calls automatically - which is exactly the behaviour we
    want to demonstrate in Level 2, not here. Re-creating the agent each turn
    guarantees that Level 1 truly has no memory of previous questions.
    """
    print("=" * 60)
    print("Strands Level 1: Hello World Agent (no tools, no memory)")
    print("Type 'quit' or 'exit' to stop.")
    print("=" * 60)

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

        # A new agent per question = no memory of earlier turns, on purpose.
        agent = build_agent()

        # Calling the agent like a function runs the full "agent loop" for
        # this one message and returns an AgentResult; printing the agent's
        # response streams/prints the text automatically for us here.
        print("\nThinking...\n")
        agent(user_question)


if __name__ == "__main__":
    main()
