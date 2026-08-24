---
title: "Microsoft Agent Framework - Getting Started"
excerpt: "If you've built AI agents on Microsoft's stack over the last couple of years, you've probably touched **Semantic Kernel** (structured, enterprise-grade orchestration) or **AutoGen** (Microsoft Research's experimental mul…"
slug: microsoft-agent-framework/part1-getting-started
artifactPath: "Microsoft Agent Framework/part1-getting-started"
tags: ["microsoft-agent-framework", "python", "ai-agents", "semantic-kernel", "getting-started"]
series: null
publishAt: "2026-07-23T22:58:00.000Z"
---
# Getting Started with Microsoft Agent Framework

If you've built AI agents on Microsoft's stack over the last couple of years, you've probably touched **Semantic Kernel** (structured, enterprise-grade orchestration) or **AutoGen** (Microsoft Research's experimental multi-agent framework). In October 2025, Microsoft merged the best ideas from both into a single, unified SDK: **Microsoft Agent Framework**.

- From **Semantic Kernel** it inherits: strong typing, dependency injection-friendly design, enterprise connectors (Azure AI Foundry, Azure OpenAI, telemetry), and production-readiness.
- From **AutoGen** it inherits: the multi-agent, graph-based **workflow** engine and the simpler "agent-first" programming model that made experimentation fast.

The result is one framework, available for **Python, .NET, and Go**, that scales from a five-line "hello agent" script to durable, multi-agent workflows with human-in-the-loop approvals — without switching SDKs halfway through a project.

This post walks through the basics in small, runnable snippets, starting from an empty folder.

## Prerequisites

- Python 3.10+
- An OpenAI API key **or** an Azure OpenAI resource (this post uses plain OpenAI to keep things minimal)
- A terminal

## Step 1 — Create a project and a virtual environment

Start with a clean folder and an isolated virtual environment so the framework's dependencies don't leak into your global Python install.

```bash
mkdir agent-framework-demo
cd agent-framework-demo

python -m venv .venv

# Activate it
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

python -V
```

```text
Python 3.12.4
```

## Step 2 — Install the framework

Agent Framework ships as a small core package plus optional provider packages, so you only pull in the dependencies you actually need. For OpenAI/Azure OpenAI:

```bash
pip install agent-framework-openai azure-identity python-dotenv
```

Verify it installed and check the version:

```bash
pip show agent-framework | findstr "Name Version"
```

```text
Name: agent-framework
Version: 1.0.0b251001001
```

## Step 3 — Configure your credentials

Agent Framework does **not** auto-load `.env` files, so create one and load it explicitly in code.

```bash
# .env
OPENAI_API_KEY=sk-...
OPENAI_CHAT_MODEL=gpt-4o-mini
```

```python
# config.py
from dotenv import load_dotenv

load_dotenv()
print("Environment variables loaded from .env")
```

## Step 4 — Create your first agent

An `Agent` is built from a **chat client** (the thing that talks to the model) plus a name and instructions. Here's the smallest possible agent:

```python
# 01_hello_agent.py
import asyncio
from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient
from dotenv import load_dotenv

load_dotenv()

async def main():
    agent = Agent(
        client=OpenAIChatClient(),
        name="HelloAgent",
        instructions="You are a friendly assistant. Keep answers brief.",
    )
    print(f"Created agent '{agent.name}' with instructions: {agent.instructions!r}")

    result = await agent.run("What is the capital of France?")
    print(f"Agent reply: {result.text}")

asyncio.run(main())
```

Run it:

```bash
python 01_hello_agent.py
```

```text
Created agent 'HelloAgent' with instructions: 'You are a friendly assistant. Keep answers brief.'
Agent reply: The capital of France is Paris.
```

## Step 5 — Stream the response

For longer answers, streaming lets you print tokens as they arrive instead of waiting for the full response.

```python
# 02_streaming.py
import asyncio
from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient
from dotenv import load_dotenv

load_dotenv()

async def main():
    agent = Agent(
        client=OpenAIChatClient(),
        name="HelloAgent",
        instructions="You are a friendly assistant.",
    )

    print("Agent (streaming): ", end="", flush=True)
    async for chunk in agent.run("Tell me a one-sentence fun fact about Paris.", stream=True):
        if chunk.text:
            print(chunk.text, end="", flush=True)
    print()

asyncio.run(main())
```

```text
Agent (streaming): The Eiffel Tower can grow about 15 cm taller in summer due to heat expansion!
```

## Step 6 — Give the agent a tool

Agents become useful once they can call your code. Any regular Python function can be turned into a **function tool** — just describe its parameters with `Annotated` + Pydantic's `Field` so the model knows what to pass.

```python
# tools.py
from typing import Annotated
from pydantic import Field

def get_weather(
    location: Annotated[str, Field(description="The city to get the weather for.")],
) -> str:
    """Get the current weather for a given location."""
    print(f"[tool call] get_weather(location={location!r})")
    return f"The weather in {location} is cloudy with a high of 15°C."
```

Register the tool on the agent by passing it in the `tools` list:

```python
# 03_agent_with_tool.py
import asyncio
from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient
from dotenv import load_dotenv
from tools import get_weather

load_dotenv()

async def main():
    agent = Agent(
        client=OpenAIChatClient(),
        name="WeatherAgent",
        instructions="You are a helpful weather assistant.",
        tools=[get_weather],
    )
    print(f"Agent '{agent.name}' registered with tools: {[t.__name__ for t in [get_weather]]}")

    result = await agent.run("What is the weather like in Amsterdam?")
    print(f"Agent reply: {result.text}")

asyncio.run(main())
```

```text
Agent 'WeatherAgent' registered with tools: ['get_weather']
[tool call] get_weather(location='Amsterdam')
Agent reply: The weather in Amsterdam is cloudy with a high of 15°C.
```

Notice the agent decided **on its own** to call `get_weather` because the question required it — you never called the function directly.

## Putting it all together

A single, complete script combining setup, a tool, and streaming output:

```python
# main.py
import asyncio
from typing import Annotated

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient
from dotenv import load_dotenv
from pydantic import Field

load_dotenv()


def get_weather(
    location: Annotated[str, Field(description="The city to get the weather for.")],
) -> str:
    """Get the current weather for a given location."""
    print(f"[tool call] get_weather(location={location!r})")
    return f"The weather in {location} is cloudy with a high of 15°C."


async def main() -> None:
    agent = Agent(
        client=OpenAIChatClient(),
        name="WeatherAgent",
        instructions="You are a helpful weather assistant. Keep answers short.",
        tools=[get_weather],
    )
    print(f"Agent '{agent.name}' is ready (model client: {type(agent.client).__name__})")

    question = "What's the weather like in Amsterdam, and give me a one-sentence fun fact about the city?"
    print(f"\nUser: {question}")
    print("Agent: ", end="", flush=True)

    async for chunk in agent.run(question, stream=True):
        if chunk.text:
            print(chunk.text, end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(main())
```

Run it end to end:

```bash
python main.py
```

```text
Agent 'WeatherAgent' is ready (model client: OpenAIChatClient)

User: What's the weather like in Amsterdam, and give me a one-sentence fun fact about the city?
Agent: [tool call] get_weather(location='Amsterdam')
The weather in Amsterdam is cloudy with a high of 15°C. Fun fact: Amsterdam has more canals than Venice!
```

## Agent Framework vs. Microsoft Foundry SDK — what's the difference?

If you're on Azure, you'll also run into the **Microsoft Foundry SDK**, and it's easy to assume it's a competitor to Agent Framework. It isn't — they sit at different layers:

| | **Foundry SDK** | **Agent Framework** |
|---|---|---|
| **What it is** | A thin client over the Foundry *project* REST API (`https://<resource>.services.ai.azure.com/api/projects/<project>`) | A higher-level, code-first agent & orchestration SDK (Python, .NET, Go) |
| **What it's for** | Direct access to Foundry Models, evaluations, and platform tools (file search, code interpreter, web search, memory, SharePoint, Fabric, MCP) tied to a specific Foundry project | Building and running agents and **multi-agent workflows** in your own code, independent of any specific backend |
| **Model backends** | Foundry project only | OpenAI, Azure OpenAI, Foundry, and other providers — swappable via the chat client |
| **Relationship** | Foundry is a *provider* — the `agent_framework.foundry` package (`FoundryChatClient`) depends on the Foundry SDK under the hood to talk to a Foundry project | Builds **on top of** the Foundry SDK (and others) rather than replacing it |
| **Use it when…** | You're building directly against Foundry-specific features: evaluations, Foundry-hosted tools, project management | You want one consistent agent API that can target Foundry today and OpenAI/Azure OpenAI tomorrow, or you need multi-agent orchestration |

In short: **the Foundry SDK is a provider client; Agent Framework is the application-level abstraction that can use it.** The `main.py` example above uses `OpenAIChatClient` directly, but swapping to Foundry only changes the client construction:

```python
# Using Foundry instead of plain OpenAI — only the client changes
import os
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential

client = FoundryChatClient(
    project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    model=os.environ["FOUNDRY_MODEL"],
    credential=AzureCliCredential(),
)
```

Everything downstream — `Agent(...)`, `tools=[...]`, `agent.run(...)` — stays exactly the same, which is the whole point of the abstraction.

## What to try next

1. **Swap providers** — point the same `Agent` code at Azure OpenAI or Azure AI Foundry by changing only the chat client (`azure_endpoint` + `AzureCliCredential`), no other code changes needed.
2. **Add more tools** — expose a database lookup, an internal API, or a calculator, and watch the model choose between them.
3. **Multiple tools and structured data** — [Part 2](/blog/microsoft-agent-framework/part2-tools-and-structured-data) shows how to build useful tool contracts and typed results.
4. **Multi-agent workflows** — [Part 3](../part3-orchestration/microsoft-agent-framework-part3-orchestration.md) covers sequential and concurrent orchestration, followed by adaptive patterns in Part 4.
4. **MCP tools** — connect an agent to an existing Model Context Protocol server instead of writing Python tools by hand.
5. **Migrate an existing Semantic Kernel agent** — Microsoft publishes a dedicated Semantic Kernel → Agent Framework migration guide since the concepts map closely.

## Why this matters

Microsoft Agent Framework closes the gap between "quick agent prototype" and "production multi-agent system" that used to force a rewrite between AutoGen and Semantic Kernel. Starting a project here means the same code you write today for a single tool-calling agent scales naturally into orchestrated, observable, enterprise-ready agent workflows tomorrow.
