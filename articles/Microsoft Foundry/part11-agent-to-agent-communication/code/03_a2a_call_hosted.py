"""
Hosted Agent Framework example using a Foundry A2A toolbox.

The toolbox contains the A2AToolboxTool. The hosted agent consumes the
toolbox through its MCP endpoint, while the toolbox calls the remote agent
through the RemoteA2A connection.
"""

import asyncio
import os
from pathlib import Path

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient, FoundryToolbox
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import A2AProtocolVersion, A2AToolboxTool
from azure.identity import AzureCliCredential
from dotenv import load_dotenv


CODE_DIR = Path(__file__).resolve().parent
load_dotenv(CODE_DIR / ".env", override=True)

PROJECT_ENDPOINT = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT = os.environ["MODEL_DEPLOYMENT"]
CONNECTION_NAME = os.environ["A2A_LOYALTY_CONNECTION_NAME"]
TOOLBOX_NAME = os.getenv("A2A_TOOLBOX_NAME", "a2a-toolbox")
TEST_PROMPT = os.getenv(
    "LOYALTY_TEST_PROMPT",
    "Can I use my loyalty points to buy the blue trail jacket in medium?",
)


async def main() -> None:
    credential = AzureCliCredential()
    project = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=credential,
    )

    connection = project.connections.get(CONNECTION_NAME)
    print(f"Using A2A connection: {CONNECTION_NAME}")
    print(f"  Connection type: {connection.type}")

    toolbox = project.toolboxes.create_version(
        name=TOOLBOX_NAME,
        description="A toolbox containing the loyalty A2A tool.",
        tools=[
            A2AToolboxTool(
                a2a_version=A2AProtocolVersion.V1_0,
                project_connection_id=connection.id,
            )
        ],
    )
    print(f"Created toolbox: {toolbox.name} (version {toolbox.version})")

    toolbox_mcp_url = (
        f"{PROJECT_ENDPOINT}/toolboxes/{toolbox.name}"
        f"/versions/{toolbox.version}/mcp?api-version=v1"
    )
    toolbox_tool = FoundryToolbox(credential, url=toolbox_mcp_url)

    async with toolbox_tool:
        agent = Agent(
            client=FoundryChatClient(
                project_endpoint=PROJECT_ENDPOINT,
                model=MODEL_DEPLOYMENT,
                credential=credential,
            ),
            instructions=(
                "You are a retail coordinator. Use the loyalty A2A toolbox "
                "to answer the customer's question. Do not invent account-specific facts."
            ),
            tools=[toolbox_tool],
        )

        print(f"Hosted agent request: {TEST_PROMPT}")
        result = await agent.run(TEST_PROMPT)
        print("--- Agent response ---")
        print(result.text)


if __name__ == "__main__":
    asyncio.run(main())
