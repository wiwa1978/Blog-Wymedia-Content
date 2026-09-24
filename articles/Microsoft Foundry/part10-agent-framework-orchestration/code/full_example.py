"""Run the Part 10 handoff, sequential, and concurrent workflows."""

import asyncio
import os

from agent_framework.orchestrations import ConcurrentBuilder, HandoffBuilder, SequentialBuilder

from common import create_agents, create_chat_client, print_outputs


async def main() -> None:
    chat_client = create_chat_client()
    agents = create_agents(chat_client)

    handoff = (
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
    sequential = SequentialBuilder(
        participants=[agents["shopper"], agents["reviewer"]]
    ).build()
    concurrent = ConcurrentBuilder(
        participants=[
            agents["shopper"],
            agents["inventory"],
            agents["loyalty"],
        ]
    ).build()

    await run_workflows(
        handoff,
        sequential,
        concurrent,
        os.getenv(
            "FRAMEWORK_TEST_PROMPT",
            "Is the blue trail jacket available in medium, and can I pay with points?",
        ),
    )


async def run_workflows(
    handoff: object,
    sequential: object,
    concurrent: object,
    question: str,
) -> None:
    handoff_events = await handoff.run(question)
    print_outputs(handoff_events, "Handoff")

    review_events = await sequential.run(
        "Recommend a waterproof trail jacket for a runner who hikes on weekends."
    )
    print_outputs(review_events, "Sequential review")

    parallel_events = await concurrent.run(question)
    print_outputs(parallel_events, "Concurrent specialists")


if __name__ == "__main__":
    asyncio.run(main())
