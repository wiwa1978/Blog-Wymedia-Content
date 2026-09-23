"""
Direct A2A protocol example: call a remote Foundry agent without routing through a caller agent.

This approach uses the A2A protocol directly with httpx and resolves the agent card.
Useful when invoking A2A from a service or script, not from within an agent workflow.
"""

import asyncio
import os

import httpx
from azure.identity import DefaultAzureCredential
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import new_text_message
from a2a.types.a2a_pb2 import Role, SendMessageRequest
from dotenv import load_dotenv


async def main():
    load_dotenv()

    # Load configuration
    project_endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    loyalty_endpoint = os.getenv("A2A_LOYALTY_ENDPOINT")
    test_prompt = os.getenv("LOYALTY_TEST_PROMPT", "Can I use my loyalty points to buy the blue trail jacket in medium?")

    if not project_endpoint or not loyalty_endpoint:
        raise ValueError("Missing FOUNDRY_PROJECT_ENDPOINT or A2A_LOYALTY_ENDPOINT in .env")

    print(f"Project endpoint: {project_endpoint}")
    print(f"Loyalty A2A endpoint: {loyalty_endpoint}")
    print(f"User request: {test_prompt}\n")

    # Authenticate and create HTTP client
    credential = DefaultAzureCredential()
    token = credential.get_token("https://ai.azure.com/.default").token

    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=httpx.Timeout(120.0),
    ) as httpx_client:
        # Resolve the agent card from the A2A endpoint
        print("--- Resolving agent card ---")
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=loyalty_endpoint,
            agent_card_path="agentCard/v0.3",
        )
        agent_card = await resolver.get_agent_card()
        print(f"Agent card resolved: {agent_card.name}")

        # Create a non-streaming A2A client
        config = ClientConfig(streaming=False, httpx_client=httpx_client)
        client = await create_client(agent=agent_card, client_config=config)

        # Send message to the remote agent
        print("--- Sending message to remote agent ---")
        message = new_text_message(test_prompt, role=Role.ROLE_USER)
        request = SendMessageRequest(message=message)

        print("--- Agent response ---")
        async for response in client.send_message(request):
            print(response)

        await client.close()
        print("\n--- A2A call completed ---")


if __name__ == "__main__":
    asyncio.run(main())
