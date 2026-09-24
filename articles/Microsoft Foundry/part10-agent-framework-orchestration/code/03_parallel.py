"""Run independent specialists with ConcurrentBuilder."""

import asyncio

from agent_framework.orchestrations import ConcurrentBuilder

from common import create_agents, create_chat_client, print_outputs


async def main() -> None:
    chat_client = create_chat_client()
    agents = create_agents(chat_client)
    workflow = ConcurrentBuilder(
        participants=[
            agents["shopper"],
            agents["inventory"],
            agents["loyalty"],
        ]
    ).build()

    request = (
        "A customer wants a blue trail jacket in medium and wants to pay with "
        "loyalty points. Identify the questions to answer before checkout."
    )
    events = await workflow.run(request)
    print_outputs(events, "Agent Framework concurrent result")


if __name__ == "__main__":
    asyncio.run(main())
