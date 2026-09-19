"""
Level 4: Vector Store / RAG Agent (Strands Agents SDK)
=============================================================

Goal (see ../../sample_problem.md): public search engines (Level 3) don't
have access to proprietary info. This level adds Retrieval Augmented
Generation (RAG) - the agent looks things up in whatever content has been
ingested into a vector store, instead of (or in addition to) what it
already knows or can find on the open web.

    User: (a question about whatever's in your knowledge base)
    AI:   (answers based on the ingested content)

Where's the ingestion code?
----------------------------------
Unlike a typical RAG example, this one doesn't build its own vector store.
It connects to an AWS **Bedrock managed Knowledge Base** that's already been
created and populated (e.g. documents uploaded to its S3 data source and
synced) via the AWS Console/CLI. This level is retrieval-only - Bedrock
handles chunking, embedding, and storage for us.
Docs: https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html

Why not `strands_tools.retrieve`?
----------------------------------
That's the "obvious" tool for this, but it's DEPRECATED in
`strands-agents-tools` (warning becomes a hard error in v0.9.0):

    "retrieve is deprecated. This warning becomes an error log in v0.9.0.
    Migration path: use MemoryManager with
    BedrockKnowledgeBaseStore(writable=False). Note the store applies no
    relevance-score floor, so filter results yourself."
    https://github.com/strands-agents/tools/blob/main/src/strands_tools/retrieve.py

So this example uses that migration path instead: Strands' `MemoryManager`
combined with `BedrockKnowledgeBaseStore`.
Docs: https://strandsagents.com/docs/user-guide/concepts/memory/bedrock-knowledge-base/

How retrieval reaches the agent
----------------------------------
Passing `memory_manager=MemoryManager(stores=[store])` to an `Agent` turns
on two things at once, by default, with no extra config:
1. A `search_memory` TOOL the model can call mid-conversation, exactly like
   the Tavily search tool in Level 3 - the model decides when it needs to
   look something up.
2. Automatic prompt INJECTION - the top search results for the user's
   question are folded into the prompt before the model even runs, so it
   often already has relevant context without calling the tool at all.
Both are harmless to leave on together; it's what makes this the simplest
working setup. If that ever feels redundant, `injection=False` on the
`MemoryManager` turns off #2 and leaves pure tool-call-driven retrieval,
matching Level 3's "the agent decides to reach for a tool" pattern.
"""

import os
import sys

import boto3
from dotenv import load_dotenv

from strands import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.memory import MemoryManager
from strands.vended_memory_stores import BedrockKnowledgeBaseStore

# Load KNOWLEDGE_BASE_ID (and anything else) from a local .env file, if present.
load_dotenv()


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

    Note: this is also the region the Bedrock Knowledge Base lookup below
    will use (boto3 resolves the same way for both clients) - if your KB
    was created in a different region, set AWS_REGION in .env to match it.
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


def build_memory_manager() -> MemoryManager:
    """
    Wire up a `MemoryManager` backed by the user's existing Bedrock
    Knowledge Base. `BedrockKnowledgeBaseStore` defaults `writable` to
    False, so a store built with just a `knowledge_base_id` is read-only -
    exactly what a lookup-only RAG agent needs.
    """
    kb_id = os.environ.get("KNOWLEDGE_BASE_ID")
    if not kb_id:
        sys.exit(
            "Missing KNOWLEDGE_BASE_ID. Copy .env.example to .env and set it "
            "to your existing Bedrock Knowledge Base's ID (AWS Console: "
            "Bedrock > Knowledge Bases), then re-run this script."
        )

    store = BedrockKnowledgeBaseStore(
        name="knowledge_base",
        description="Content ingested into the user's Bedrock managed Knowledge Base.",
        config={"knowledge_base_id": kb_id},
    )
    return MemoryManager(stores=[store])


def build_agent() -> Agent:
    """
    Create the Level 4 agent: same conversational memory setup as Levels
    2-3, but equipped with a Bedrock Knowledge Base lookup instead of (or
    alongside) web search.
    """
    conversation_manager = SlidingWindowConversationManager(window_size=20)

    return Agent(
        system_prompt=(
            "You are a Q&A assistant that answers questions using the "
            "content stored in your knowledge base. Ground every answer "
            "in the retrieved content - if the knowledge base doesn't "
            "contain the answer, say so rather than guessing."
        ),
        memory_manager=build_memory_manager(),
        conversation_manager=conversation_manager,
        # Same reasoning as Level 3: explicitly pinned to Nova Pro (tool use
        # support, keeps this off the shared Anthropic quota) via its
        # cross-region inference profile, resolved for your region above.
        model=_nova_pro_model_id(),
    )


def main() -> None:
    """CLI loop, structurally identical to Level 2/3 (same agent reused
    across turns for memory). No MCP connection to hold open here, so
    unlike Level 3 there's no `with` block needed."""
    print("=" * 60)
    print("Strands Level 4: Knowledge Base RAG Agent (Bedrock KB + memory)")
    print("Ask a question about whatever's in your knowledge base.")
    print("Type 'quit' or 'exit' to stop.")
    print("=" * 60)

    agent = build_agent()

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

        print("\nThinking (may search the knowledge base)...\n")
        # Strands will automatically:
        #   1. Fold in any relevant knowledge-base results for this question
        #      (automatic injection).
        #   2. Ask the model what to do next; if it wants more detail, it
        #      can call the `search_memory` tool itself.
        #   3. Repeat until the model produces a final text answer.
        # All of that happens inside this single call.
        agent(user_question)


if __name__ == "__main__":
    main()
