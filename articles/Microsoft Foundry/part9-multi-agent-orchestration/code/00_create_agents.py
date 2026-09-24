"""Create the specialist and handoff agents used by the Part 9 examples."""

from common import create_all_agents, create_project_client


def main() -> None:
    with create_project_client() as project_client:
        create_all_agents(project_client)


if __name__ == "__main__":
    main()
