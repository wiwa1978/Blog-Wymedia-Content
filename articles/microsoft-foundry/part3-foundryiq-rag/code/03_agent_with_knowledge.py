"""
Part 3 - Step 3: Connect a Foundry agent to the Foundry IQ knowledge base.

This mirrors the two-step pattern from the official docs
(azure/foundry/agents/how-to/foundry-iq-connect):

  1. Create a *project connection* to the knowledge base's MCP endpoint, using
     the project's own managed identity for auth (ProjectManagedIdentity /
     RemoteTool). There's no Python SDK surface for this yet, so it's a plain
     ARM REST call.
  2. Create an agent whose MCPTool references that connection via
     project_connection_id (instead of a static bearer token, like the
     Toolbox example in Part 2 uses).

Then it opens an interactive chat loop so you can ask questions grounded in
the PDF you indexed in 01_create_search_index.py / 02_create_knowledge_base.py.
"""

import requests
import sys
from azure.ai.projects.models import MCPTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from _common import (
    AGENT_NAME,
    KNOWLEDGE_BASE_NAME,
    MODEL_DEPLOYMENT,
    PROJECT_CONNECTION_NAME,
    PROJECT_RESOURCE_ID,
    SEARCH_ENDPOINT,
    agent_reference,
    create_clients,
)

MCP_ENDPOINT = (
    f"{SEARCH_ENDPOINT}/knowledgebases/{KNOWLEDGE_BASE_NAME}/mcp"
    "?api-version=2026-08-01-preview"
)

INSTRUCTIONS = """
You are a helpful assistant that must use the knowledge base to answer all
questions from the user. You must never answer from your own knowledge.
If you cannot find the answer in the knowledge base, respond with
"I don't know based on the indexed document."
When you use information from the knowledge base, mention the page number(s)
it came from.
""".strip()


def create_project_connection(credential: DefaultAzureCredential) -> None:
    """Create (or update) the ARM project connection the MCPTool will reference."""
    token_provider = get_bearer_token_provider(
        credential, "https://management.azure.com/.default"
    )
    url = (
        f"https://management.azure.com{PROJECT_RESOURCE_ID}/connections/"
        f"{PROJECT_CONNECTION_NAME}?api-version=2025-10-01-preview"
    )
    body = {
        "name": PROJECT_CONNECTION_NAME,
        "type": "Microsoft.MachineLearningServices/workspaces/connections",
        "properties": {
            "authType": "ProjectManagedIdentity",
            "category": "RemoteTool",
            "target": MCP_ENDPOINT,
            "isSharedToAll": True,
            "audience": "https://search.azure.com/",
            "metadata": {"ApiType": "Azure"},
        },
    }
    response = requests.put(
        url,
        headers={
            "Authorization": f"Bearer {token_provider()}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=30,
    )
    response.raise_for_status()
    print(f"Project connection '{PROJECT_CONNECTION_NAME}' created or updated successfully.")


def create_agent(project) -> object:
    mcp_kb_tool = MCPTool(
        server_label="knowledge-base",
        server_url=MCP_ENDPOINT,
        require_approval="never",
        allowed_tools=["knowledge_base_retrieve"],
        project_connection_id=PROJECT_CONNECTION_NAME,
    )
    agent = project.agents.create_version(
        agent_name=AGENT_NAME,
        definition=PromptAgentDefinition(
            model=MODEL_DEPLOYMENT,
            instructions=INSTRUCTIONS,
            tools=[mcp_kb_tool],
        ),
    )
    print(f"Agent '{agent.name}' created or updated successfully (version {agent.version}).")
    return agent


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    credential = DefaultAzureCredential()
    create_project_connection(credential)

    project, openai_client = create_clients()
    agent = create_agent(project)

    conversation = openai_client.conversations.create()
    print("\nAsk questions about the indexed PDF. Type 'exit' to quit.\n")

    while True:
        question = input("You: ").strip()
        if not question or question.lower() in {"exit", "quit"}:
            break

        response = openai_client.responses.create(
            conversation=conversation.id,
            input=question,
            extra_body=agent_reference(agent.name),
        )
        print(f"Agent: {response.output_text}\n")
