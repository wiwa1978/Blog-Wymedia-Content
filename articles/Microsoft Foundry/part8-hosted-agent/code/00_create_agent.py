"""
Part 8: Hosted agent with MCP tools integration.

This agent uses MCP tools to query information and demonstrate
how hosted agents can orchestrate MCP-based workflows.

Usage:
  Local development:
    # Terminal 1: Start the agent server
    python 00_create_agent.py

    # Terminal 2: Send a request
    python 01_invoke_local.py

  Production deployment:
    azd deploy
"""
import os
from pathlib import Path

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.ai.agentserver.core.tasks import set_resilient_tasks_enabled
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from tools import read_markdown_file, query_json_data


load_dotenv(Path(__file__).with_name(".env"), override=True)


INSTRUCTIONS = """
You are a knowledge assistant with access to local documentation and data tools.

Your responsibilities:
- Use read_markdown_file to search documentation by file path.
- Use query_json_data to search product catalogs, FAQs, and structured knowledge.
- Always try to find and cite the relevant source.
- Be concise and focus on the user's question.

When answering questions about features, capabilities, or troubleshooting:
1. Search the available documentation first.
2. Provide the most relevant information with a source reference.
3. If no documentation exists, say so and offer general guidance.
"""


def main() -> None:
    """Start the hosted-agent Responses server managed by Foundry Agent Service."""
    # These values are loaded from the colocated .env file for local
    # development and can be injected as environment variables in production.
    #
    # DefaultAzureCredential automatically handles:
    # - Local: Uses Azure CLI credentials from `az login`
    # - Production: Uses Managed Identity assigned to the container
    client = FoundryChatClient(
        project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
        model=os.environ["MODEL_DEPLOYMENT"],
        credential=DefaultAzureCredential(),
    )

    agent = Agent(
        client=client,
        instructions=INSTRUCTIONS,
        tools=[read_markdown_file, query_json_data],
        # History is managed by the hosting infrastructure, so the agent
        # itself doesn't need to store conversation state.
        default_options={"store": False},
    )

    # ResponsesHostServer supplies the port, readiness endpoint, and
    # Responses protocol adapter expected by the hosted-agent platform.
    set_resilient_tasks_enabled(True)
    ResponsesHostServer(agent).run()


if __name__ == "__main__":
    main()
