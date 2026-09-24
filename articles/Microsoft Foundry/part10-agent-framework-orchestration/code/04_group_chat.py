"""Run a bounded group-chat workflow with shared conversation context.

Three specialists (shopper, inventory, loyalty) each give feedback on the same
request in a fixed order, all sharing one growing conversation. The reviewer
speaks last and synthesizes the three specialist inputs into a single final
answer. The workflow only terminates once the reviewer has spoken, and only
the reviewer's message (plus the orchestrator's own status message) is
surfaced as the workflow's final `output`. The specialists' turns are
surfaced as `intermediate` output only, representing internal deliberation
that should not reach the customer.
"""

import asyncio

from agent_framework.orchestrations import GroupChatBuilder, GroupChatState

from common import create_agents, create_chat_client

SHOPPER_NAME = "part10-shopper"
INVENTORY_NAME = "part10-inventory"
LOYALTY_NAME = "part10-loyalty"
REVIEWER_NAME = "part10-reviewer"

# Each specialist speaks once, in this fixed order, then the reviewer
# synthesizes everything that was said into one final answer.
SPEAKING_ORDER = [SHOPPER_NAME, INVENTORY_NAME, LOYALTY_NAME, REVIEWER_NAME]


def specialist_then_synthesize(state: GroupChatState) -> str:
    """Let each specialist give feedback once, then hand the floor to the
    reviewer to synthesize a single final answer."""

    return SPEAKING_ORDER[state.current_round % len(SPEAKING_ORDER)]


def synthesis_has_closed(conversation: list) -> bool:
    """Terminate once the reviewer has produced the synthesized answer, i.e.
    once every specialist plus the reviewer has spoken exactly once."""

    return (
        len(conversation) >= len(SPEAKING_ORDER) + 1
        and conversation[-1].author_name == REVIEWER_NAME
    )


async def main() -> None:
    chat_client = create_chat_client()
    agents = create_agents(chat_client)
    workflow = GroupChatBuilder(
        participants=[
            agents["shopper"],
            agents["inventory"],
            agents["loyalty"],
            agents["reviewer"],
        ],
        selection_func=specialist_then_synthesize,
        termination_condition=synthesis_has_closed,
        output_from=[agents["reviewer"]],
        intermediate_output_from=[agents["shopper"], agents["inventory"], agents["loyalty"]],
    ).build()

    question = (
        "A customer wants a waterproof trail jacket in blue, size medium. "
        "They also want to know if it is in stock and whether they can pay "
        "with loyalty points. Give one combined answer covering product fit, "
        "availability, and loyalty payment options."
    )
    events = await workflow.run(question)

    print("\n--- Agent Framework group-chat result ---")
    print("Internal deliberation (not shown to the customer):")
    for response in events.get_intermediate_outputs():
        for message in response.messages:
            author = message.author_name or "assistant"
            print(f"[{author}]\n{message.text}\n")

    print("Final answer to the customer:")
    for response in events.get_outputs():
        for message in response.messages:
            author = message.author_name or "assistant"
            print(f"[{author}]\n{message.text}\n")


if __name__ == "__main__":
    asyncio.run(main())
