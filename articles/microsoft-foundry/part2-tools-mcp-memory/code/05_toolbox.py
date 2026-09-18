"""Part 2.5 - Bundle multiple tools behind a versioned Toolbox."""

import asyncio
import json
import os

import httpx2
from azure.ai.projects.models import (
    MCPToolboxTool,
    MCPTool,
    PromptAgentDefinition,
    ToolSearchToolboxTool,
    WebSearchToolboxTool,
)
from azure.identity import DefaultAzureCredential
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from _common import MODEL_DEPLOYMENT, PROJECT_ENDPOINT, agent_reference, create_clients


project, openai = create_clients()
toolbox_name = os.getenv("TOOLBOX_NAME", "foundry-tools")
toolbox_version = project.toolboxes.create_version(
    name=toolbox_name,
    description="Toolbox with web search, an MCP server, and tool search.",
    tools=[
        WebSearchToolboxTool(name="web-search"),
        MCPToolboxTool(
            server_label="microsoft-learn",
            server_url="https://learn.microsoft.com/api/mcp",
            require_approval="never",
        ),
        ToolSearchToolboxTool(name="tool-search"),
    ],
)
print(f"Created toolbox: {toolbox_version.name}, version: {toolbox_version.version}")


async def verify_toolbox() -> None:
    """List the tools exposed by the Toolbox MCP endpoint."""
    toolbox_url = (
        f"{PROJECT_ENDPOINT}/toolboxes/{toolbox_name}/versions/"
        f"{toolbox_version.version}/mcp?api-version=v1"
    )
    token = DefaultAzureCredential().get_token(
        "https://ai.azure.com/.default"
    ).token
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx2.AsyncClient(headers=headers) as http_client:
        async with streamable_http_client(
            toolbox_url, http_client=http_client
        ) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                print(f"Tools found: {len(tools_result.tools)}")
                for tool in tools_result.tools:
                    print(f"  - {tool.name}: {(tool.description or '')[:80]}")


asyncio.run(verify_toolbox())

toolbox_url = (
    f"{PROJECT_ENDPOINT}/toolboxes/{toolbox_name}/versions/"
    f"{toolbox_version.version}/mcp?api-version=v1"
)
# The Toolbox's own MCP endpoint requires authentication, just like the
# verify_toolbox() call above. Without this token the agent service gets a
# 424 (Failed Dependency) when it tries to reach the Toolbox.
toolbox_token = DefaultAzureCredential().get_token(
    "https://ai.azure.com/.default"
).token
agent = project.agents.create_version(
    agent_name="ToolboxAgent",
    definition=PromptAgentDefinition(
        model=MODEL_DEPLOYMENT,
        instructions=(
            "You have a Toolbox with multiple tools (web search, Microsoft "
            "Learn documentation, etc.), but they aren't listed directly — "
            "first call tool_search to find the best tool for the question, "
            "then call_tool to invoke it. Always pick the tool that best "
            "fits the question: Microsoft Learn for documentation, web "
            "search for current events or anything not in Microsoft docs."
        ),
        tools=[
            MCPTool(
                server_label="foundry-toolbox",
                server_url=toolbox_url,
                authorization=toolbox_token,
                require_approval="never",
            )
        ],
    ),
)
print(f"Agent created for Toolbox: {agent.name}, version: {agent.version}")

conversation = openai.conversations.create()


def ask(question: str) -> None:
    """Send a question and print the answer plus which toolbox tool ran."""
    response = openai.responses.create(
        conversation=conversation.id,
        input=question,
        extra_body=agent_reference(agent.name),
    )
    print(response.output_text)

    # Every toolbox invocation shows up as an mcp_call for "call_tool" — the
    # actual tool name (e.g. "web-search" or "microsoft-learn") is in its
    # arguments, so we parse that out to see which tool the model picked.
    for item in response.output:
        if item.type == "mcp_call" and item.name == "call_tool":
            args = json.loads(item.arguments)
            print(f"[toolbox routed to: {args.get('name')}]")


# Question 1: this is a documentation lookup, so the model should pick the
# Microsoft Learn MCP tool inside the toolbox.
print("--- Question 1 (expect Microsoft Learn tool) ---")
ask(
    "Find the official Microsoft Learn documentation for Azure AI Foundry "
    "MCP tools."
)

# Question 2: this asks about live, current information that isn't in
# Microsoft Learn docs, so the model should pick the web search tool instead
# — the same agent, same toolbox, but a different tool chosen automatically.
print("\n--- Question 2 (expect web search tool) ---")
ask("What is today's top news headline about Microsoft?")
