"""Part 2.2 - Search tabular text data through a vector store."""

from pathlib import Path

from azure.ai.projects.models import FileSearchTool, PromptAgentDefinition
from openai import OpenAIError

from _common import MODEL_DEPLOYMENT, agent_reference, create_clients


def print_chunk_preview(path: Path, lines_per_chunk: int = 2) -> None:
    """Show an educational approximation of how the source may be chunked."""
    lines = path.read_text(encoding="utf-8").splitlines()
    print("Local chunk preview (the service may use different boundaries):")
    for number, start in enumerate(range(0, len(lines), lines_per_chunk), start=1):
        chunk = "\n".join(lines[start : start + lines_per_chunk])
        print(f"\n  Chunk {number}:\n{chunk}")


project, openai = create_clients()
orders_path = Path(__file__).with_name("orders.txt")
print_chunk_preview(orders_path)

vector_store = openai.vector_stores.create(name="OrdersKnowledgeBase")
print(f"Created vector store: {vector_store.id}")

try:
    with orders_path.open("rb") as file_handle:
        vector_store_file = openai.vector_stores.files.upload_and_poll(
            vector_store_id=vector_store.id,
            file=file_handle,
        )
except OpenAIError:
    openai.vector_stores.delete(vector_store.id)
    raise
print(f"Indexed file: {vector_store_file.id}, status: {vector_store_file.status}")

agent = project.agents.create_version(
    agent_name="FileSearchAgent",
    definition=PromptAgentDefinition(
        model=MODEL_DEPLOYMENT,
        instructions=(
            "You are a helpful agent that answers questions about orders. "
            "Use file search to look up facts from the uploaded tabular data."
        ),
        tools=[FileSearchTool(vector_store_ids=[vector_store.id])],
    ),
    description="File search agent for order data.",
)
print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")

conversation = openai.conversations.create()
response = openai.responses.create(
    conversation=conversation.id,
    input="How many orders are in the file, and what is the largest one?",
    extra_body=agent_reference(agent.name),
)
print(response.output_text)
