"""Delete only the agents created by this Part 9 sample."""

from common import AGENT_NAMES, create_project_client


def main() -> None:
    with create_project_client() as project_client:
        for name in AGENT_NAMES.values():
            project_client.agents.delete(agent_name=name, force=True)
            print(f"Deleted {name}")


if __name__ == "__main__":
    main()
