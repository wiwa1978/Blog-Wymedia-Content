"""Full Part 9 example: create agents, route a request, and execute specialists."""

import os

from common import (
    AGENT_NAMES,
    create_all_agents,
    create_project_client,
    parse_json_response,
    response_text,
    run_agent,
)


def main() -> None:
    question = os.getenv(
        "TEST_PROMPT",
        "Is the blue trail jacket available in medium, and can I pay with points?",
    )
    with create_project_client() as project_client:
        create_all_agents(project_client)
        print("--- Routing specialist is answering ---")
        handoff = parse_json_response(
            run_agent(project_client, AGENT_NAMES["handoff"], question)
        )
        target = handoff.get("target")
        if target not in ("shopper", "inventory", "loyalty"):
            raise RuntimeError(f"Unsupported handoff target: {target!r}")

        print(f"Routing to: {target}")
        print(f"--- {target.capitalize()} specialist is answering ---")
        specialist_response = run_agent(
            project_client,
            AGENT_NAMES[target],
            question,
        )
        print("Part 9 multi-agent result")
        print("========================")
        print(f"Selected specialist: {target}")
        print(f"Confidence: {handoff.get('confidence', 'unknown')}")
        print(f"Reason: {handoff.get('reason', '')}")
        print()
        print(response_text(specialist_response))


if __name__ == "__main__":
    main()
