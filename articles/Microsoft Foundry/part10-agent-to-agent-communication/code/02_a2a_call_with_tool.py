"""
Routed A2A call using a Foundry agent with the GA A2ATool.

This is the second, more advanced example. It requires a pre-configured
RemoteA2A project connection in Foundry.
If you get "Failed to fetch agent card: 404", see the troubleshooting guide:
https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/agent-to-agent-authentication#troubleshooting

The direct A2A approach (01_a2a_call_direct.py) is simpler
and doesn't require connection setup—it works by calling the remote agent's
A2A endpoint directly with explicit authentication.

This script demonstrates:
1. Request routing logic (selecting which specialist agent to call)
2. Creating a temporary caller agent with A2ATool
3. Using the Responses API to invoke the caller agent
4. The A2ATool uses a pre-configured RemoteA2A connection to reach the remote agent
"""

import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    A2AProtocolVersion,
    A2ATool,
    PromptAgentDefinition,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


CODE_DIR = Path(__file__).resolve().parent
load_dotenv(CODE_DIR / ".env", override=True)

PROJECT_ENDPOINT = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT = os.environ["MODEL_DEPLOYMENT"]
A2A_CONNECTION_NAMES = {
    "shopper": os.getenv("A2A_SHOPPER_CONNECTION_NAME", ""),
    "inventory": os.getenv("A2A_INVENTORY_CONNECTION_NAME", ""),
    "loyalty": os.environ["A2A_LOYALTY_CONNECTION_NAME"],
}
CALLER_AGENT_NAME = os.getenv("A2A_CALLER_AGENT_NAME", "orcha2a-caller")
TEST_PROMPT = os.getenv(
    "LOYALTY_TEST_PROMPT",
    "Can I use my loyalty points to buy the blue trail jacket in medium?",
)


def route_request(request: str) -> str:
    """Choose a specialist before the A2A request is created."""
    text = request.lower()
    if any(word in text for word in ("point", "discount", "membership", "reward")):
        return "loyalty"
    if any(word in text for word in ("stock", "available", "shipping", "delivery")):
        return "inventory"
    return "shopper"


def main() -> None:
    project = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )

    target = route_request(TEST_PROMPT)
    connection_name = A2A_CONNECTION_NAMES[target]
    if not connection_name:
        raise RuntimeError(
            f"No A2A connection is configured for routed target '{target}'. "
            f"Set A2A_{target.upper()}_CONNECTION_NAME in .env."
        )
    
    # Retrieve the A2A connection from Foundry.
    # The connection must be pre-configured in the Foundry project with:
    #  - Type: RemoteA2A
    #  - Endpoint: the target agent's A2A protocol URL
    #  - Auth: Entra Agent Identity or API key
    print(f"Looking up A2A connection: {connection_name}")
    connection = project.connections.get(connection_name)
    print(f"  Connection ID: {connection.id}")
    print(f"  Connection type: {connection.type}")
    
    # Create the A2ATool referencing the connection.
    # The tool will use the connection's stored endpoint and auth to reach the remote agent.
    a2a_tool = A2ATool(
        a2a_version=A2AProtocolVersion.V1_0,
        project_connection_id=connection.id,
    )

    # Create a temporary caller agent that has the A2ATool.
    # When invoked via Responses API, the agent can use the tool to call the remote agent.
    caller = None
    try:
        caller = project.agents.create_version(
            agent_name=CALLER_AGENT_NAME,
            definition=PromptAgentDefinition(
                model=MODEL_DEPLOYMENT,
                instructions=(
                    f"You are a retail coordinator. The application routed this request "
                    f"to the remote {target} specialist. Use the remote agent to answer "
                    "the customer's question clearly. Do not invent account-specific facts."
                ),
                tools=[a2a_tool],
            ),
        )

        print(f"\nCaller agent: {caller.name} (version {caller.version})")
        print(f"User request: {TEST_PROMPT}")
        print(f"Routed to specialist: {target}")
        print(f"Using A2A connection: {connection_name}")
        print("--- Agent response ---\n")

        # Invoke the caller agent via the Responses API.
        # The agent will use the A2ATool to call the remote agent.
        openai = project.get_openai_client()
        response = openai.responses.create(
            tool_choice="required",
            input=TEST_PROMPT,
            extra_body={
                "agent_reference": {
                    "name": caller.name,
                    "type": "agent_reference",
                }
            },
        )

        print(response.output_text)
    finally:
        if caller is not None:
            project.agents.delete_version(
                agent_name=caller.name,
                agent_version=caller.version,
            )
            print(f"\nDeleted temporary caller version {caller.version}.")


if __name__ == "__main__":
    main()
