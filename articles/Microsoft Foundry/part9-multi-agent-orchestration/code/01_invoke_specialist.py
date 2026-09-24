"""Invoke one specialist directly, without orchestration."""

import os

from common import AGENT_NAMES, create_project_client, response_text, run_agent


def main() -> None:
    domain = os.getenv("SPECIALIST", "inventory")
    question = os.getenv(
        "SPECIALIST_PROMPT",
        "Do you have a blue trail running jacket in medium?",
    )
    if domain not in AGENT_NAMES or domain == "handoff":
        raise ValueError("SPECIALIST must be shopper, inventory, or loyalty.")

    with create_project_client() as project_client:
        print(f"--- {domain.capitalize()} specialist is answering ---")
        response = run_agent(project_client, AGENT_NAMES[domain], question)
        print(response_text(response))


if __name__ == "__main__":
    main()
