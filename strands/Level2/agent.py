"""
Level 2: Conversational Memory Agent (Strands Agents SDK)
============================================================

Goal (see ../../sample_problem.md): LLMs are stateless by default - each
call to a model has no idea what happened in previous calls. This level
teaches an agent to remember earlier turns of the SAME conversation, so a
user can say "My name is Sakhi..." and later ask "What career options fit
my interests?" and get an answer that actually uses the earlier context.

How does Strands give an agent memory?
----------------------------------------
A `strands.Agent` object keeps its own running transcript in `agent.messages`
(a list of user/assistant messages). As long as you keep calling the SAME
Agent instance, every new call automatically includes the full prior history
when talking to the LLM - you don't have to manage a chat history list
yourself. This is different from Level 1, where we deliberately created a
NEW Agent every turn to prevent this.

Docs: https://strandsagents.com/docs/user-guide/concepts/agents/conversation-management/

Why not let history grow forever?
------------------------------------
If a conversation runs for a long time, the transcript can grow past the
model's context window (and cost more tokens per call). Strands solves this
with a "conversation manager" that trims/summarizes older messages. We use
the built-in `SlidingWindowConversationManager`, which just keeps the most
recent N messages and drops the rest - simple and predictable for a learning
example.
"""

import boto3

from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager


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
    Create ONE Agent that we will reuse for the entire chat session.

    Reusing the same Agent instance across multiple `agent(...)` calls is
    what gives us memory - Strands appends every turn to `agent.messages`
    and replays that history to the model on the next call automatically.
    """
    # Keep only the most recent 20 messages (roughly 10 user/assistant pairs,
    # since tool calls also count as messages) in the context sent to the
    # model. Older turns are simply dropped - this is a deliberately simple
    # memory strategy, good enough for a short interactive chat.
    conversation_manager = SlidingWindowConversationManager(
        window_size=20,
    )

    return Agent(
        system_prompt=(
            "You are a friendly AI career advisor. Use everything the user "
            "has told you earlier in this conversation (their name, "
            "interests, background, etc.) to personalize your answers. "
            "Keep responses concise."
        ),
        conversation_manager=conversation_manager,
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
    CLI loop that reuses ONE agent for the whole session, so it remembers
    everything said earlier - unlike Level 1, which forgot everything
    between questions.
    """
    print("=" * 60)
    print("Strands Level 2: Conversational Memory Agent")
    print("Try: 'My name is Sakhi, I'm interested in compiler design and ML'")
    print("Then follow up with: 'What career options fit my interests?'")
    print("Type 'quit' or 'exit' to stop.")
    print("=" * 60)

    # Created ONCE, outside the loop - this is the key difference vs Level 1.
    agent = build_agent()

    while True:
        try:
            user_message = input("\nYour message: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_message:
            continue
        if user_message.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        print("\nThinking...\n")
        # Because `agent` is the same object every time, Strands automatically
        # includes everything said earlier in this session as context.
        agent(user_message)


if __name__ == "__main__":
    main()
