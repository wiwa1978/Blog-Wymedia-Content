"""Shared configuration and helpers for the Part 9 examples."""

import json
import os
from pathlib import Path
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


CODE_DIR = Path(__file__).resolve().parent
load_dotenv(CODE_DIR / ".env", override=True)

PROJECT_ENDPOINT = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT = os.environ["MODEL_DEPLOYMENT"]
AGENT_PREFIX = os.getenv("AGENT_PREFIX", "part9-")

AGENT_NAMES = {
    "shopper": f"{AGENT_PREFIX}shopper",
    "inventory": f"{AGENT_PREFIX}inventory",
    "loyalty": f"{AGENT_PREFIX}loyalty",
    "reviewer": f"{AGENT_PREFIX}reviewer",
    "handoff": f"{AGENT_PREFIX}handoff",
}

SPECIALIST_INSTRUCTIONS = {
    "shopper": (
        "You are the shopper specialist. Help users choose products and explain "
        "which option best fits their stated goal. Do not answer inventory or "
        "loyalty questions in depth; route those to the appropriate specialist. "
        "Answer the user directly and do not describe the handoff process or mention other agents."
    ),
    "inventory": (
        "You are the inventory specialist. Answer questions about availability, "
        "stock levels, and delivery estimates. Do not invent stock numbers. If "
        "the request is not about inventory, say which specialist should handle it. "
        "Answer the user directly and do not describe the handoff process or mention other agents."
    ),
    "loyalty": (
        "You are the loyalty specialist. Explain loyalty points, discounts, and "
        "membership benefits. Do not invent account-specific balances. Answer the "
        "user directly and do not describe the handoff process or mention other agents."
    ),
    "reviewer": (
        "You are a response reviewer. Check the supplied draft for unsupported "
        "claims, unclear assumptions, and missing caveats. Return a corrected, "
        "concise answer. Do not invent facts."
    ),
}

HANDOFF_INSTRUCTIONS = """You are a handoff classifier for a shopping assistant.
Choose exactly one target from shopper, inventory, or loyalty.
Return only JSON in this shape:
{"target": "shopper|inventory|loyalty", "confidence": 0.0, "reason": "..."}
Use shopper for product selection, inventory for stock or delivery, and loyalty
for points, discounts, or membership benefits."""


def create_project_client() -> AIProjectClient:
    return AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )


def create_agent(project_client, name: str, instructions: str, description: str) -> None:
    from azure.ai.projects.models import PromptAgentDefinition

    agent = project_client.agents.create_version(
        agent_name=name,
        description=description,
        definition=PromptAgentDefinition(
            model=MODEL_DEPLOYMENT,
            instructions=instructions,
        ),
    )
    print(f"Created {agent.name} version {agent.version}")


def create_all_agents(project_client) -> None:
    for domain, instructions in SPECIALIST_INSTRUCTIONS.items():
        create_agent(
            project_client,
            AGENT_NAMES[domain],
            instructions,
            f"Part 9 {domain} specialist",
        )
    create_agent(
        project_client,
        AGENT_NAMES["handoff"],
        HANDOFF_INSTRUCTIONS,
        "Part 9 handoff classifier",
    )


def run_agent(
    project_client: AIProjectClient,
    agent_name: str,
    user_input: str,
    previous_response_id: str | None = None,
) -> Any:
    """Invoke a versioned prompt agent through the Responses API."""
    responses = project_client.get_openai_client(agent_name=agent_name).responses
    arguments: dict[str, Any] = {"input": user_input}
    if previous_response_id:
        arguments["previous_response_id"] = previous_response_id
    return responses.create(**arguments)


def response_text(response: Any) -> str:
    return response.output_text.strip()


def parse_json_response(response: Any) -> dict[str, Any]:
    """Parse a handoff response while surfacing malformed agent output."""
    text = response_text(response)
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Handoff agent returned invalid JSON: {text}") from exc
    if not isinstance(value, dict):
        raise RuntimeError("Handoff agent returned JSON, but not an object.")
    return value
