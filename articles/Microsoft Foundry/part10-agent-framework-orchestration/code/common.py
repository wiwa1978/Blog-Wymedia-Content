"""Shared configuration and Agent Framework helpers for Part 10."""

import os

from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv


CODE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(CODE_DIR, ".env"), override=True)

PROJECT_ENDPOINT = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT = os.environ["MODEL_DEPLOYMENT"]


def create_chat_client() -> FoundryChatClient:
    return FoundryChatClient(
        project_endpoint=PROJECT_ENDPOINT,
        model=MODEL_DEPLOYMENT,
        credential=AzureCliCredential(),
    )


def create_agents(chat_client: FoundryChatClient) -> dict[str, object]:
    handoff_history = {"require_per_service_call_history_persistence": True}
    return {
        "triage": chat_client.as_agent(
            name="part10-triage",
            description="Routes retail questions to the right specialist.",
            instructions=(
                "You are the retail triage specialist. Route each request to exactly "
                "one specialist: shopper for product selection, inventory for stock "
                "or delivery, and loyalty for points or membership questions."
            ),
            **handoff_history,
        ),
        "shopper": chat_client.as_agent(
            name="part10-shopper",
            description="Handles product selection and recommendations.",
            instructions=(
                "You are the shopper specialist. Help users choose products and "
                "explain which option best fits their goal. Do not invent product facts."
            ),
            **handoff_history,
        ),
        "inventory": chat_client.as_agent(
            name="part10-inventory",
            description="Handles availability and delivery questions.",
            instructions=(
                "You are the inventory specialist. Answer availability and delivery "
                "questions, but never invent live stock numbers or delivery dates."
            ),
            **handoff_history,
        ),
        "loyalty": chat_client.as_agent(
            name="part10-loyalty",
            description="Handles points, discounts, and membership benefits.",
            instructions=(
                "You are the loyalty specialist. Explain points, discounts, and "
                "membership benefits without inventing account-specific balances."
            ),
            **handoff_history,
        ),
        "reviewer": chat_client.as_agent(
            name="part10-reviewer",
            description="Reviews a draft for unsupported claims and assumptions.",
            instructions=(
                "You are a response reviewer. Check the previous response for "
                "unsupported claims and missing assumptions, then return a concise "
                "corrected answer."
            ),
            **handoff_history,
        ),
    }


def print_outputs(events: object, heading: str) -> None:
    print(f"\n--- {heading} ---")
    outputs = events.get_outputs()
    for response in outputs:
        for message in response.messages:
            author = message.author_name or "assistant"
            print(f"[{author}]\n{message.text}\n")
