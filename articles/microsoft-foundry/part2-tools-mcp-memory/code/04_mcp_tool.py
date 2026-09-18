"""Part 2.4 - Attach an external MCP server as an agent tool."""

import os
import sys

from azure.ai.projects.models import MCPTool, PromptAgentDefinition
from openai.types.responses.response_input_param import (
    McpApprovalResponse,
    ResponseInputParam,
)

from _common import MODEL_DEPLOYMENT, agent_reference, create_clients


project, openai = create_clients()
connection_name = os.getenv("MCP_CONNECTION_NAME")
if connection_name in {"", "my-mcp-connection", "my-github-mcp-server"}:
    connection_name = None

tool_settings = {
    "server_label": "learn",
    "server_url": os.getenv(
        "MCP_SERVER_URL",
        "https://learn.microsoft.com/api/mcp",
    ),
    "require_approval": "always",
}
if connection_name:
    tool_settings["project_connection_id"] = connection_name

mcp_tool = MCPTool(**tool_settings)

agent = project.agents.create_version(
    agent_name="MCPAgent",
    definition=PromptAgentDefinition(
        model=MODEL_DEPLOYMENT,
        instructions="Use MCP tools as needed.",
        tools=[mcp_tool],
    ),
)
print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")

conversation = openai.conversations.create()
question = " ".join(sys.argv[1:]).strip() or (
    "Find the Microsoft Learn documentation for Azure AI Foundry MCP tools "
    "and summarize what the MCP tool does."
)
response = openai.responses.create(
    conversation=conversation.id,
    input=question,
    extra_body=agent_reference(agent.name),
)

while True:
    # The model pauses here when the MCP server requests permission.
    input_list: ResponseInputParam = []
    for item in response.output:
        # A response can contain many item types; only approval requests need
        # an application response.
        if item.type == "mcp_approval_request":
            # Some response items do not expose a name, so use a safe label.
            tool_name = getattr(item, "name", "<unknown>")
            # Replace this prompt with your own policy or approval UI.
            decision = input(
                f"MCP approval requested for tool '{tool_name}'. "
                "Allow it? [y/N]: "
            ).strip().lower()
            input_list.append(
                McpApprovalResponse(
                    type="mcp_approval_response",
                    approval_request_id=item.id,
                    # The ID links this decision to the original request.
                    approve=decision in {"y", "yes"},
                )
            )

    if not input_list:
        break

    # Send the decision back so the model can continue.
    response = openai.responses.create(
        conversation=conversation.id,
        input=input_list,
        extra_body=agent_reference(agent.name),
    )

print(response.output_text)
