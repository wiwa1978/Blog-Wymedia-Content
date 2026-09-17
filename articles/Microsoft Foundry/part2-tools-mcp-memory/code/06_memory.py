"""Part 2.6 - Create a memory store and attach it to an agent."""

import os
import time
import uuid
from datetime import timedelta

from azure.ai.projects.models import (
    MemorySearchOptions,
    MemorySearchPreviewTool,
    MemoryStoreDefaultDefinition,
    MemoryStoreDefaultOptions,
    PromptAgentDefinition,
)
from azure.core.exceptions import HttpResponseError

from _common import MODEL_DEPLOYMENT, agent_reference, create_clients


project, openai = create_clients()
memory_store_name = os.getenv("MEMORY_STORE_NAME", "foundry-memory")
embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# Use a fresh scope per run (unless overridden) so this demo is self-contained.
# The memory store itself persists across runs, but memories are partitioned
# by scope - reusing "user_123" every time would keep piling facts from past
# runs into the same bucket, so a later search/recall could surface stale
# memories from a previous test instead of only what you just taught it.
scope = os.getenv("MEMORY_SCOPE") or f"user_{uuid.uuid4().hex[:8]}"

options = MemoryStoreDefaultOptions(
    chat_summary_enabled=True,
    user_profile_enabled=True,
    procedural_memory_enabled=True,
    default_ttl_seconds=timedelta(days=30),
    user_profile_details=(
        "Avoid irrelevant or sensitive data, such as age, financials, "
        "precise location, and credentials."
    ),
)
definition = MemoryStoreDefaultDefinition(
    chat_model=MODEL_DEPLOYMENT,
    embedding_model=embedding_model,
    options=options,
)

try:
    memory_store = project.beta.memory_stores.create(
        name=memory_store_name,
        definition=definition,
        description="Memory store with procedural memory and 30-day default TTL.",
    )
    print(f"Created memory store: {memory_store.name}")
except HttpResponseError as error:
    # The store persists across runs (unlike a Toolbox, it doesn't version),
    # so re-running this script is safe: reuse the existing store instead of
    # failing on "already exists".
    if error.error and error.error.code == "bad_request" and "already exists" in str(error):
        memory_store = project.beta.memory_stores.get(name=memory_store_name)
        print(f"Reusing existing memory store: {memory_store.name}")
    else:
        raise

agent = project.agents.create_version(
    agent_name="MemoryAgent",
    definition=PromptAgentDefinition(
        model=MODEL_DEPLOYMENT,
        instructions="You are a helpful assistant that answers general questions.",
        tools=[
            MemorySearchPreviewTool(
                memory_store_name=memory_store_name,
                scope=scope,
                update_delay=1,
            )
        ],
    ),
)
print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")
print(f"Using memory scope: {scope}")

# Step 1: have a conversation where the user states a fact worth remembering.
# The memory search tool extracts and stores durable facts like this in the
# background as the conversation happens. Let the reader type their own fact
# instead of hard-coding one, so the recall step below feels genuinely live.
default_fact = "I only drink oat milk lattes, no other coffee. Please remember that."
user_fact = input(f"Tell the agent something to remember [{default_fact}]: ").strip() or default_fact

conversation = openai.conversations.create()
teach_response = openai.responses.create(
    conversation=conversation.id,
    input=user_fact,
    extra_body=agent_reference(agent.name),
)
print(f"Agent replied: {teach_response.output_text}")

# Memory extraction runs asynchronously after the response, so give it a
# moment before searching (in production, update_delay=1 above still means
# near-instant extraction, but a short buffer avoids a race on first run).
# Statements with several facts at once can take a little longer to extract.
time.sleep(8)

# Step 2: in a NEW, unrelated context, search the memory store directly to
# prove the fact was captured and is retrievable independent of the original
# conversation. Ask a natural, generic question rather than echoing the fact
# back verbatim - that way the search genuinely has to retrieve what was
# stored instead of just matching on shared wording.
recall_question = "What do you remember about me?"
query_message = {
    "role": "user",
    "content": recall_question,
    "type": "message",
}
search_response = project.beta.memory_stores.search_memories(
    name=memory_store_name,
    scope=scope,
    items=[query_message],
    options=MemorySearchOptions(max_memories=5),
)
print(f"Found {len(search_response.memories)} memories")
for memory in search_response.memories:
    print(f"  - {memory.memory_item.memory_id}: {memory.memory_item.content}")

# Step 3: ask the agent the same question in a brand-new conversation. The
# memory search tool retrieves the stored fact automatically, so the agent
# can answer correctly without the user repeating themselves.
new_conversation = openai.conversations.create()
recall_response = openai.responses.create(
    conversation=new_conversation.id,
    input=recall_question,
    extra_body=agent_reference(agent.name),
)
print(f"Agent recalled: {recall_response.output_text}")
