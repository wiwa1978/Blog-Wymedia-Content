"""Route a request with Microsoft Agent Framework's HandoffBuilder."""

import asyncio
import os

from agent_framework.orchestrations import HandoffBuilder

from common import create_agents, create_chat_client, print_outputs


async def main() -> None:
    question = os.getenv(
        "FRAMEWORK_TEST_PROMPT",
        "Can I use my loyalty points on this order?",
    )

    chat_client = create_chat_client()
    agents = create_agents(chat_client)
    workflow = (
        HandoffBuilder(
            name="part10-retail-handoff",
            participants=[
                agents["triage"],
                agents["shopper"],
                agents["inventory"],
                agents["loyalty"],
            ],
        )
        .with_start_agent(agents["triage"])
        .add_handoff(
            agents["triage"],
            [agents["shopper"], agents["inventory"], agents["loyalty"]],
        )
        .build()
    )

    events = await workflow.run(question)
    print_outputs(events, "Agent Framework handoff result")


if __name__ == "__main__":
    asyncio.run(main())
