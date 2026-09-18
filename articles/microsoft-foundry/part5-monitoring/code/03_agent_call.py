"""Send one traced Foundry agent request and print its three portal views."""
import json
import os
import sys
import time
from datetime import timedelta
from importlib import import_module

from dotenv import load_dotenv

load_dotenv()
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

configure_tracing = import_module("01_configure_tracing").configure_tracing
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus


def print_trace_view(response_id: str) -> None:
    query = f"""
    union withsource=TableName isfuzzy=true requests, dependencies, traces
    | where tostring(customDimensions["gen_ai.response.id"]) == "{response_id}"
    | project timestamp, name=coalesce(name, message), duration, operation_Id,
        target, resultCode, success, source=TableName
    | order by timestamp asc
    """
    result = LogsQueryClient(DefaultAzureCredential()).query_resource(
        os.environ["APPINSIGHTS_RESOURCE_ID"],
        query,
        timespan=timedelta(days=1),
    )
    if result.status != LogsQueryStatus.SUCCESS:
        raise RuntimeError(f"Application Insights query failed: {result}")

    table = result.tables[0] if result.tables else None
    print("\n=== TRACE VIEW ===")
    if not table or not table.rows:
        print("No matching trace found yet. Ingestion can take a few minutes.")
        return
    for row in table.rows:
        values = dict(zip(table.columns, row))
        print(
            f"{values['timestamp']} | {values['source']} | {values['name']} | "
            f"duration={values['duration']} | operation_id={values['operation_Id']} | "
            f"success={values['success']}"
        )


def print_conversation_and_response_views(client: object, conversation_id: str, response_id: str) -> None:
    print("\n=== CONVERSATION VIEW ===")
    conversation = client.conversations.retrieve(conversation_id)
    print(conversation.model_dump_json(indent=2))
    items = client.conversations.items.list(
        conversation_id=conversation_id,
        order="asc",
    )
    print(json.dumps([item.model_dump(mode="json") for item in items], indent=2))

    print("\n=== RESPONSE VIEW ===")
    response = client.responses.retrieve(response_id)
    print(response.model_dump_json(indent=2))


def main() -> None:
    project = AIProjectClient(
        endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential(),
    )
    agent = project.agents.create_version(
        agent_name=os.environ["FOUNDRY_AGENT_NAME"],
        definition=PromptAgentDefinition(
            model=os.environ["MODEL_DEPLOYMENT"],
            instructions="You are concise and helpful.",
        ),
    )
    client = project.get_openai_client()
    conversation = client.conversations.create()
    started = time.perf_counter()
    response = client.responses.create(
        conversation=conversation.id,
        input="In one sentence, explain why request traces are useful.",
        extra_body={
            "agent_reference": {
                "name": agent.name,
                "id": agent.id,
                "type": "agent_reference",
            }
        },
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    print(f"Agent response ID: {response.id}")
    print(f"Agent trace conversation ID: {conversation.id}")
    print(f"Agent latency: {elapsed_ms:.0f} ms")
    print(f"Agent output: {response.output_text}")
    usage = getattr(response, "usage", None)
    if usage:
        print(
            "Agent tokens: "
            f"input={getattr(usage, 'input_tokens', None)} "
            f"output={getattr(usage, 'output_tokens', None)} "
            f"total={getattr(usage, 'total_tokens', None)}"
        )
    print()
    print(
        f"Agent '{agent.name}' (version {agent.version}) was left in place so you can "
        "inspect it and its Traces tab in the Foundry portal (Agents > "
        f"{agent.name} > Traces)."
    )
    print_trace_view(response.id)
    print_conversation_and_response_views(client, conversation.id, response.id)


if __name__ == "__main__":
    configure_tracing()
    main()
