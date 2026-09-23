---
title: "Deploying Hosted Agents"
excerpt: "Deploy scalable Microsoft Foundry hosted agents using source packages, containers, Azure Container Registry, and Azure Developer CLI."
slug: microsoft-foundry/part10-deploying-hosted-agents
artifactPath: "Microsoft Foundry/part10-deploying-hosted-agents"
tags: ["azure", "ai-foundry", "sdk", "python", "agents"]
series: {"slug":"microsoft-foundry","title":"Microsoft Foundry","part":10}
publishAt: "2026-08-09T09:04:00.000Z"
---
# Microsoft Foundry SDK: Part 10 – Deploying Hosted Agents

You've built sophisticated agents in the Foundry project environment (parts 1–8). But production demands **persistent, scalable infrastructure**: agents that run 24/7, scale to thousands of concurrent users, and remain isolated from development workspaces.

After monitoring, evaluation, and guardrails in [Parts 5–7](/blog/microsoft-foundry/part5-monitoring), this post walks through **Hosted Agent deployment**—containerizing your agent, pushing to Azure Container Registry, provisioning managed compute, and invoking via production endpoints. You'll see both the **Python SDK path** (full control, explicit steps) and the **`azd` shortcut** (automated, convention-over-configuration).

## Prerequisites

- Azure CLI authenticated: `az account show`
- A Foundry project with `azure-ai-projects` >= 2.3.0
- Docker installed and running locally
- An existing agent (use part 1 template, add tools from part 2 if desired)
- Container Registry access (create via `az acr create --resource-group <rg> --name <name> --sku Basic`)
- Foundry Project Manager role on your project

## Step 1: Choose Your Deployment Method

Before diving into code, you need to pick **how** you're deploying your agent. Foundry supports **three approaches**, each with different tradeoffs:

| Deployment Method | Best For | Packaging | Inner Loop | Container Registry |
|---|---|---|---|---|
| **Source Code (ZIP)** | Most teams, fastest dev cycle, Python/C# only | `main.py` + `requirements.txt` | `azd up` or SDK | Not needed |
| **Container (Docker)** | Multi-language agents, existing Docker workflows, complex dependencies | Dockerfile → ACR | Docker build/push | Required (ACR) |
| **Azure Developer CLI** | First-time deployments, guided setup, both paths | Chosen by tooling | Interactive wizards | Auto-created if needed |

**Recommendation for beginners**: Start with **Source Code (ZIP)** – smallest upload, no Docker needed, platform handles dependency resolution.

This section covers **both Container and Source Code paths**. The container path is perfect if you have existing Docker expertise or multi-language requirements; the ZIP path is simpler and faster for Python/C# development.

## Step 2: Understand Hosted Agent Protocols

A Hosted agent can expose multiple **protocols**, each for a different client pattern:

| Protocol | URL Path | Use Case | Streaming |
|----------|----------|----------|-----------|
| **Responses** | `/responses` | Conversational, chat-like | ✓ Yes (SSE) |
| **Invocations** | `/invocations` | Webhook/non-conversational, batch | ✗ No |
| **Invocations WS** | `/invocations_ws` | WebSocket, voice/bidirectional | ✓ Yes |

For this post, we'll focus on **Responses** (most common). Your container can expose multiple protocols—the SDK lets you choose which versions to deploy:

```python
from azure.ai.projects.models import ProtocolVersionRecord, AgentEndpointProtocol

# Define which protocols this agent will expose
protocol_versions = [
    ProtocolVersionRecord(
        protocol=AgentEndpointProtocol.RESPONSES,
        version="1.0.0"
    ),
    # Optionally add more:
    # ProtocolVersionRecord(
    #     protocol=AgentEndpointProtocol.INVOCATIONS,
    #     version="1.0.0"
    # )
]

print(f"✓ Protocols defined: {[p.protocol for p in protocol_versions]}")
```
