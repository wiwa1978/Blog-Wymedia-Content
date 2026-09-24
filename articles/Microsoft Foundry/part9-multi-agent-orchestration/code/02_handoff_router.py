"""Route a request through the handoff agent to one specialist."""

import os
import json

from common import (
    AGENT_NAMES,
    create_project_client,
    parse_json_response,
    response_text,
    run_agent,
)


def main() -> None:
    question = os.getenv(
        "TEST_PROMPT",
        "Can I use my loyalty points on this order?",
    )
    with create_project_client() as project_client:
        print(f"User request: {question}")
        print("Handoff agent is classifying the request...")
        print("--- Routing specialist is answering ---")
        handoff = parse_json_response(
            run_agent(project_client, AGENT_NAMES["handoff"], question)
        )
        print(json.dumps(handoff, indent=2))
        target = handoff.get("target")
        if target not in ("shopper", "inventory", "loyalty"):
            raise RuntimeError(f"Unsupported handoff target: {target!r}")

        print(f"Routing to: {target}")
        specialist = run_agent(project_client, AGENT_NAMES[target], question)
        print(f"\n--- {target.capitalize()} specialist is answering ---")
        print(response_text(specialist))


if __name__ == "__main__":
    main()
