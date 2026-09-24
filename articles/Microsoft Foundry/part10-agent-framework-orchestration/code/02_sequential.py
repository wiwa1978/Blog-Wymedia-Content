"""Run a draft-then-review workflow with SequentialBuilder."""

import asyncio

from agent_framework.orchestrations import SequentialBuilder

from common import create_agents, create_chat_client, print_outputs


async def main() -> None:
    chat_client = create_chat_client()
    agents = create_agents(chat_client)
    workflow = SequentialBuilder(
        participants=[agents["shopper"], agents["reviewer"]]
    ).build()

    request = (
        "Recommend a waterproof trail jacket to a runner who hikes on weekends. "
        "Explain the recommendation and its assumptions."
    )
    events = await workflow.run(request)
    print_outputs(events, "Agent Framework sequential result")


if __name__ == "__main__":
    asyncio.run(main())
