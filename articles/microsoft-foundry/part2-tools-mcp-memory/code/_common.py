"""Shared configuration for the Part 2 examples."""

import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

PROJECT_ENDPOINT = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT = os.getenv("MODEL_DEPLOYMENT", "gpt-5.1-mini")


def create_clients() -> tuple[AIProjectClient, object]:
    """Create the Foundry project client and its OpenAI-compatible client."""
    project = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )
    return project, project.get_openai_client()


def agent_reference(agent_name: str) -> dict:
    """Return the agent reference payload used by Responses API calls."""
    return {"agent_reference": {"name": agent_name, "type": "agent_reference"}}
