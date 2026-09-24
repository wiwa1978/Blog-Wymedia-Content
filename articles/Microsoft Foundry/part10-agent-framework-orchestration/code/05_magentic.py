"""Run a bounded Magentic workflow with a manager and specialist participants."""

import asyncio

from agent_framework import Agent
from agent_framework.orchestrations import MagenticBuilder

from common import create_agents, create_chat_client, print_outputs


async def main() -> None:
    chat_client = create_chat_client()
    agents = create_agents(chat_client)
    manager = Agent(
        client=chat_client,
        name="part10-magentic-manager",
        description="Plans and coordinates a complex retail investigation.",
        instructions=(
            "Coordinate the specialist team to answer the user's question. "
            "Create a practical plan, delegate useful work, replan when needed, "
            "and return one concise final answer. The specialists have no real "
            "inventory, catalog, or loyalty-account data to check, so they cannot "
            "confirm live facts such as exact stock or point balances - that is "
            "expected, not a failure. Treat the task as satisfied once the "
            "specialists have covered fit, availability, and loyalty payment, "
            "even if their answer is a clear checklist of what still needs to be "
            "confirmed (for example, against a real inventory system) rather than "
            "confirmed facts. Do not keep delegating the same question hoping for "
            "different facts to appear."
        ),
    )
    workflow = MagenticBuilder(
        participants=[
            agents["shopper"],
            agents["inventory"],
            agents["loyalty"],
        ],
        manager_agent=manager,
        intermediate_output_from=[
            agents["shopper"],
            agents["inventory"],
            agents["loyalty"],
        ],
        max_round_count=6,
        max_stall_count=2,
        max_reset_count=1,
    ).build()

    question = (
        "Prepare a checkout readiness brief for a blue trail jacket in medium. "
        "Cover product fit, availability questions, and loyalty-point constraints."
    )
    events = await workflow.run(question)
    print_outputs(events, "Agent Framework Magentic result")


if __name__ == "__main__":
    asyncio.run(main())
