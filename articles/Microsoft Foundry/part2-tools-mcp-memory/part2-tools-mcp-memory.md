---
title: "MCP servers, tools, toolboxes, and memory"
excerpt: "A practical guide to extending Microsoft Foundry agents with web search, file search, custom functions, MCP, toolboxes, and persistent memory."
slug: microsoft-foundry/part2-tools-mcp-memory
artifactPath: "Microsoft Foundry/part2-tools-mcp-memory"
tags: ["azure", "ai-foundry", "sdk", "python", "agents", "mcp", "toolbox", "memory"]
series: {"slug":"microsoft-foundry","title":"Microsoft Foundry","part":2}
publishAt: "2026-07-01T07:12:00.000Z"
---
# Part 2 - Beyond the basics: MCP servers, tools, toolboxes, and memory in the Microsoft Foundry SDK

In [Part 1 - Getting started with Microsoft Foundry SDK](/blog/microsoft-foundry/part1-getting-started) we created a Foundry resource, a project, deployed a model, and built our first **Prompt agent** with `PromptAgentDefinition`. That agent could chat — but it couldn't search the web, read your files, call your functions, or remember anything between conversations.

This post is the "rest of the SDK": a rundown of the tool-related API calls Foundry Agent Service supports, shown as small, runnable snippets in **increasing order of complexity**:

1. A single built-in tool (web search)
2. A knowledge source (file search over an uploaded CSV)
3. A custom function tool (your own Python code)
4. An external MCP server as a tool
5. Multiple tools bundled behind a **Toolbox**
6. A **memory store** so agents remember things across conversations

Every snippet builds on the project you created in part 1 and prints out what it created, so you can see exactly what's happening.

## Prerequisites

```bash
pip install "azure-ai-projects>=2.3.0" azure-identity openai
```

```python
import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

PROJECT_ENDPOINT = "https://<your-account>.services.ai.azure.com/api/projects/<your-project>"
MODEL_DEPLOYMENT = "gpt-5-mini"  # the deployment you created in part 1

project = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)
openai = project.get_openai_client()

print(f"Connected to project: {PROJECT_ENDPOINT}")
```

Every tool below is passed into `PromptAgentDefinition(tools=[...])` — the shape you already know from part 1. What changes is which `Tool` object you put in that list.

## 1. Start simple: attach the web search tool

The easiest way to give an agent live, real-world information is the built-in **web search tool**. No extra resource, no toolbox — just add it to the agent's `tools` list.

```python
from azure.ai.projects.models import PromptAgentDefinition, WebSearchTool, WebSearchApproximateLocation

agent = project.agents.create_version(
    agent_name="WebSearchAgent",
    definition=PromptAgentDefinition(
        model=MODEL_DEPLOYMENT,
        instructions="You are a helpful assistant that can search the web.",
        tools=[
            WebSearchTool(
                user_location=WebSearchApproximateLocation(
                    country="GB", city="London", region="London"
                )
            )
        ],
    ),
    description="Agent for web search.",
)
print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")

response = openai.responses.create(
    tool_choice="required",
    input="What is today's date and the weather in Seattle?",
    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
)
print(response.output_text)

# Print the sources the model actually used
for item in response.output:
    if item.type == "message":
        for content in item.content:
            for annotation in getattr(content, "annotations", []):
                if annotation.type == "url_citation":
                    print(f"Source: {annotation.url}")
```

**What just happened:** the model decided a web search was needed, the service ran it, and the response comes back with inline URL citations you can print or show to users.

> There's also `BingGroundingTool` for a paid, dedicated Bing resource with more control (custom search scopes, market/language pinning). Start with `WebSearchTool` — it's the fastest path to a grounded answer.

## 2. Add a knowledge source: file search over a CSV

Web search answers questions about the world. Most real agents also need to answer questions about **your data** — a product catalog, a CSV export, internal docs. The **file search tool** does this by indexing files into a vector store.

```python
from pathlib import Path
from azure.ai.projects.models import FileSearchTool

# Any file works here — including a CSV export of your data
csv_path = Path("orders.csv")

# 1. Create a vector store and upload the file into it
vector_store = openai.vector_stores.create(name="OrdersKnowledgeBase")
print(f"Created vector store: {vector_store.id}")

with csv_path.open("rb") as file_handle:
    vector_store_file = openai.vector_stores.files.upload_and_poll(
        vector_store_id=vector_store.id,
        file=file_handle,
    )
print(f"Indexed file: {vector_store_file.id}, status: {vector_store_file.status}")

# 2. Attach the vector store to an agent via the file search tool
agent = project.agents.create_version(
    agent_name="OrdersAgent",
    definition=PromptAgentDefinition(
        model=MODEL_DEPLOYMENT,
        instructions=(
            "You are a helpful agent that answers questions about orders. "
            "Use file search to look up facts from the uploaded CSV."
        ),
        tools=[FileSearchTool(vector_store_ids=[vector_store.id])],
    ),
    description="File search agent for order data.",
)
print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")

conversation = openai.conversations.create()
response = openai.responses.create(
    conversation=conversation.id,
    input="How many orders are in the file, and what's the largest one?",
    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
)
print(response.output_text)

# Cleanup
project.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
openai.vector_stores.delete(vector_store.id)
print("Agent and vector store deleted")
```

**What just happened:** the CSV was chunked and embedded into a vector store, and the file search tool lets the model retrieve relevant rows before answering — a lightweight RAG (retrieval-augmented generation) pattern with almost no extra code.

## 3. Add a custom function tool

Web search and file search cover *external* and *your data* knowledge. Sometimes the agent needs to call **your own code** — a database lookup, an internal API, a calculation. That's the **function tool**.

```python
import json
from azure.ai.projects.models import Tool, FunctionTool
from openai.types.responses.response_input_param import FunctionCallOutput, ResponseInputParam

def get_horoscope(sign: str) -> str:
    """Generate a horoscope for the given astrological sign."""
    return f"{sign}: Next Tuesday you will befriend a baby otter."

# Describe the function so the model knows it exists and how to call it
func_tool = FunctionTool(
    name="get_horoscope",
    parameters={
        "type": "object",
        "properties": {
            "sign": {"type": "string", "description": "An astrological sign like Taurus or Aquarius"},
        },
        "required": ["sign"],
        "additionalProperties": False,
    },
    description="Get today's horoscope for an astrological sign.",
    strict=True,
)

tools: list[Tool] = [func_tool]

agent = project.agents.create_version(
    agent_name="FunctionToolAgent",
    definition=PromptAgentDefinition(
        model=MODEL_DEPLOYMENT,
        instructions="You are a helpful assistant that can use function tools.",
        tools=tools,
    ),
)
print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")

conversation = openai.conversations.create()
response = openai.responses.create(
    input="What is my horoscope? I am an Aquarius.",
    conversation=conversation.id,
    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
)

# The model doesn't run your function — YOUR code has to detect the request and run it
input_list: ResponseInputParam = []
for item in response.output:
    if item.type == "function_call" and item.name == "get_horoscope":
        result = get_horoscope(**json.loads(item.arguments))
        print(f"Executed local function -> {result}")
        input_list.append(
            FunctionCallOutput(type="function_call_output", call_id=item.call_id, output=json.dumps({"horoscope": result}))
        )

# Send the tool output back so the model can finish its answer
response = openai.responses.create(
    input=input_list,
    conversation=conversation.id,
    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
)
print(f"Final answer: {response.output_text}")

project.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
```

**What just happened:** unlike web/file search, function tools are a two-way handshake — the model *requests* a call, your app *executes* it locally, and you *submit the result back*. This is the pattern to reach for whenever the agent needs to touch your systems, not just public or indexed data. (Note: function tools expire 10 minutes after the run starts, so submit your output promptly.)

## 4. Attach an external MCP server as a tool

The [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) is quickly becoming the standard way tools are exposed. Instead of writing a `FunctionTool` yourself, you can point the agent directly at any MCP server — for example GitHub's hosted MCP server.

```python
from azure.ai.projects.models import MCPTool
from openai.types.responses.response_input_param import McpApprovalResponse, ResponseInputParam

MCP_CONNECTION_NAME = "my-mcp-connection"  # a project connection storing the server's auth

mcp_tool = MCPTool(
    server_label="api-specs",
    server_url="https://api.githubcopilot.com/mcp",
    require_approval="always",
    project_connection_id=MCP_CONNECTION_NAME,
)

agent = project.agents.create_version(
    agent_name="MCPAgent",
    definition=PromptAgentDefinition(
        model=MODEL_DEPLOYMENT,
        instructions="Use MCP tools as needed",
        tools=[mcp_tool],
    ),
)
print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")

conversation = openai.conversations.create()
response = openai.responses.create(
    conversation=conversation.id,
    input="What is my username in my GitHub profile?",
    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
)

# MCP tools support human-in-the-loop approval before each call
input_list: ResponseInputParam = []
for item in response.output:
    if item.type == "mcp_approval_request":
        print(f"MCP approval requested for tool: {getattr(item, 'name', '<unknown>')}")
        input_list.append(
            McpApprovalResponse(type="mcp_approval_response", approval_request_id=item.id, approve=True)
        )

if input_list:
    response = openai.responses.create(
        conversation=conversation.id,
        input=input_list,
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )
print(response.output_text)
```

**What just happened:** `require_approval="always"` means every tool call the MCP server wants to make comes back to your app as an `mcp_approval_request` first — useful while you trust a new server, or for anything sensitive. Set it to `"never"` once you're comfortable letting calls run automatically.

## 5. Put multiple tools behind a Toolbox

So far each agent got exactly one tool. Real agents usually need several — and re-declaring the same set of tools on every agent gets repetitive fast. A **Toolbox** is a versioned, reusable, MCP-compatible *bundle* of tools that any agent (or even non-Foundry framework like LangGraph or Agent Framework) can connect to as a single MCP endpoint.

```python
from azure.ai.projects.models import MCPToolboxTool, ToolSearchToolboxTool, WebSearchToolboxTool

toolbox_version = project.toolboxes.create_version(
    name="my-toolbox",
    description="Toolbox with web search, an MCP server, and tool search",
    tools=[
        WebSearchToolboxTool(),
        MCPToolboxTool(
            server_label="myserver",
            server_url="https://your-mcp-server.example.com",
            require_approval="never",
            project_connection_id="my-key-auth-connection",
        ),
        ToolSearchToolboxTool(),  # lets the agent discover tools dynamically as the toolbox grows
    ],
)
print(f"Created toolbox: {toolbox_version.name}, version: {toolbox_version.version}")

# List all versions of the toolbox
versions = list(project.toolboxes.list_toolbox_versions(name="my-toolbox"))
print(f"Toolbox has {len(versions)} version(s)")
```

> A toolbox allows at most **one unnamed tool per type** (web search, file search, code interpreter, Azure AI Search). Add more instances of the same tool type by giving each a unique `name`.

Once created, the toolbox exposes its own MCP endpoint:

```text
https://<account>.services.ai.azure.com/api/projects/<project>/toolboxes/my-toolbox/versions/1/mcp?api-version=v1
```

You can verify what tools are live on that endpoint before wiring it into any agent:

```python
import asyncio
from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession

toolbox_url = (
    f"{PROJECT_ENDPOINT}/toolboxes/my-toolbox/versions/{toolbox_version.version}/mcp?api-version=v1"
)
token = DefaultAzureCredential().get_token("https://ai.azure.com/.default").token
headers = {"Authorization": f"Bearer {token}"}

async def verify_toolbox():
    async with streamablehttp_client(toolbox_url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            print(f"Tools found: {len(tools_result.tools)}")
            for tool in tools_result.tools:
                print(f"  - {tool.name}: {(tool.description or '')[:80]}")

asyncio.run(verify_toolbox())
```

**What just happened:** you now have a single, versioned, reusable endpoint that bundles several tools. A Prompt agent can attach it with a plain `MCPTool` pointing at the toolbox's endpoint; a Hosted agent built with Microsoft Agent Framework can connect to the same endpoint using `MCPStreamableHTTPTool`. Either way, you manage the tool set in one place instead of duplicating it per agent.

## 6. Give the agent memory across conversations

Everything so far lives inside a single run or conversation. A **memory store** lets an agent remember facts about a user (preferences, prior context) and recall them automatically in future, unrelated conversations.

```python
import os
from datetime import timedelta
from azure.ai.projects.models import MemoryStoreDefaultDefinition, MemoryStoreDefaultOptions

# Memory needs both a chat model deployment and an embedding model deployment
CHAT_MODEL = MODEL_DEPLOYMENT
EMBEDDING_MODEL = "text-embedding-3-small"  # deploy this in Foundry first

memory_store_name = "my_memory_store"

options = MemoryStoreDefaultOptions(
    chat_summary_enabled=True,
    user_profile_enabled=True,
    procedural_memory_enabled=True,
    default_ttl_seconds=timedelta(days=30),
    user_profile_details="Avoid irrelevant or sensitive data, such as age, financials, precise location, and credentials",
)

definition = MemoryStoreDefaultDefinition(
    chat_model=CHAT_MODEL,
    embedding_model=EMBEDDING_MODEL,
    options=options,
)

memory_store = project.beta.memory_stores.create(
    name=memory_store_name,
    definition=definition,
    description="Memory store with procedural memory and 30-day default TTL",
)
print(f"Created memory store: {memory_store.name}")
```

Now attach the **memory search tool** to a Prompt agent so it reads/writes memories during conversations:

```python
from azure.ai.projects.models import MemorySearchPreviewTool

scope = "user_123"  # associate memories with a specific user

agent = project.agents.create_version(
    agent_name="MemoryAgent",
    definition=PromptAgentDefinition(
        model=CHAT_MODEL,
        instructions="You are a helpful assistant that answers general questions",
        tools=[
            MemorySearchPreviewTool(
                memory_store_name=memory_store_name,
                scope=scope,
                update_delay=1,  # wait 1s of inactivity before updating memories (use ~300s in production)
            )
        ],
    ),
)
print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")
```

And search for what the agent has remembered:

```python
from azure.ai.projects.models import MemorySearchOptions

query_message = {"role": "user", "content": "What are my coffee preferences?", "type": "message"}

search_response = project.beta.memory_stores.search_memories(
    name=memory_store_name,
    scope=scope,
    items=[query_message],
    options=MemorySearchOptions(max_memories=5),
)
print(f"Found {len(search_response.memories)} memories")
for memory in search_response.memories:
    print(f"  - {memory.memory_item.memory_id}: {memory.memory_item.content}")
```

**What just happened:** the memory store extracts durable facts from conversations (respecting `scope`, TTL, and the privacy guidance you configure in `user_profile_details`), and the memory search tool lets any agent attached to that store retrieve relevant memories before responding — so a user doesn't have to repeat themselves in a new conversation.

## Putting it together

A realistic agent usually combines several of these: a Toolbox for external capabilities, a Function tool for your own systems, and a Memory store for continuity.

```python
from azure.ai.projects.models import PromptAgentDefinition, MCPTool, MemorySearchPreviewTool

full_agent = project.agents.create_version(
    agent_name="FullFeaturedAgent",
    definition=PromptAgentDefinition(
        model=MODEL_DEPLOYMENT,
        instructions="You are a helpful assistant with tools, a toolbox, and memory.",
        tools=[
            func_tool,  # custom function from step 3
            MCPTool(  # this agent's own toolbox, exposed as an MCP endpoint
                server_label="my-toolbox",
                server_url=toolbox_url,
                require_approval="never",
            ),
            MemorySearchPreviewTool(memory_store_name=memory_store_name, scope=scope),
        ],
    ),
)
print(f"Full-featured agent created (id: {full_agent.id}, version: {full_agent.version})")
```

## Cleanup

```python
project.agents.delete_version(agent_name=full_agent.name, agent_version=full_agent.version)
project.beta.memory_stores.delete(memory_store_name)
print("Cleaned up agent and memory store")
```

## What to try next

- Swap `WebSearchTool` for `BingGroundingTool` once you need a paid Bing resource with custom search scopes.
- Explore the other Toolbox tool types: Azure AI Search, Code Interpreter, OpenAPI, Agent-to-Agent, Browser Automation, Fabric IQ, and Work IQ.
- Try `require_approval="always"` on MCP tools in development, and only relax it to `"never"` once you trust the server.
- Look at `project.beta.memory_stores.update_memory` / `delete_memory` / `list_memories` for full memory item CRUD — not just search.
- If you're building custom agent *code* rather than a config-only Prompt agent, look at **Microsoft Agent Framework** — it can consume the exact same Toolbox MCP endpoint via `MCPStreamableHTTPTool`.

## Closing note

Every tool type here — web search, file search, function tools, MCP, toolboxes, memory — plugs into the same `tools=[...]` list on `PromptAgentDefinition` you learned in part 1. Once you're comfortable with that one pattern, adding new capabilities to an agent is mostly a matter of picking the right `Tool` class and grounding it with a resource (a vector store, a connection, a toolbox, a memory store). Start small, verify each tool in isolation with `print()` statements like the ones above, then compose them together once you trust each piece.

---

## Full Sample Code

The complete working example for this post is available on GitHub:

**[part2_tools_mcp_memory.py](code/part2_tools_mcp_memory.py)**

Run it locally:
```bash
python part2_tools_mcp_memory.py
```

---

*Sources: [Microsoft Foundry documentation](https://learn.microsoft.com/azure/foundry/), [Tool resources in Prompt Agent Definition](https://learn.microsoft.com/azure/foundry/concepts/agents/tools), [MCP Tool in Agent Definition](https://learn.microsoft.com/azure/foundry/concepts/agents/tools-mcp), [Memory Stores](https://learn.microsoft.com/azure/foundry/concepts/agents/memory), [Azure AI Search Integration](https://learn.microsoft.com/azure/foundry/how-to/agents/tools-search).*
