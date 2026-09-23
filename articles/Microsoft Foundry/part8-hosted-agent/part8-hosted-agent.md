---
title: "Hosted Agents"
excerpt: "Build, test, deploy, and operate a hosted Microsoft Foundry agent that uses Python tools to access local data and services."
slug: microsoft-foundry/part8-hosted-agent
artifactPath: "Microsoft Foundry/part8-hosted-agent"
tags: ["azure", "ai-foundry", "sdk", "python", "agents", "hosted-agents", "mcp"]
series: {"slug":"microsoft-foundry","title":"Microsoft Foundry","part":8}
publishAt: "2026-09-29T18:01:00.000Z"
---
# Hosted Agents

The earlier parts created **prompt agents**: the model, instructions, and optional tools were configured in Foundry. That approach is a useful starting point because Foundry manages the runtime for us. But what happens when the agent needs code that we own—for example, code that reads a private knowledge source, calls an internal API, or coordinates an MCP server?

That is where a **Hosted agent** fits. A Hosted agent is a Python application that you own and deploy to Foundry Agent Service. Foundry runs the application and communicates with it through the Responses protocol, while your code owns the agent's instructions, tool definitions, and execution logic. This gives us more control, but it also means that we must understand the application lifecycle: create the agent, run it, test it, package it, and deploy it.

## Hosted agent versus prompt agent

The distinction matters before we write any code. A **prompt agent** keeps its instructions, model configuration, and optional tools in the Foundry project. Foundry operates the agent loop. A **hosted agent** moves that runtime into application code that we package and deploy; Foundry still provides the managed endpoint, scaling, and hosting platform.

| Dimension | Prompt agent | Hosted agent |
| --- | --- | --- |
| **Definition** | Instructions + model + tools | Customer code + framework + dependencies |
| **Runtime** | Foundry-operated harness | Customer logic running on Foundry-managed container compute |
| **Portal experience** | Create, edit, version, and test the agent | Deploy code, then test and operate the deployed version |
| **Endpoint** | Managed | Managed |
| **Best fit** | Rapid development with less customization | Custom code, orchestration, protocols, or runtime behavior |

## What we will build

We choose a hosted agent because it must execute Python code that reads a Markdown file and exposes that operation as a tool. The same boundary is useful for controlled access to databases, internal APIs, or MCP servers. The trade-off is that we now own the application lifecycle, packaging, dependency management, and version deployment.

We will build that understanding in small steps. First, we create a deliberately small knowledge assistant with a tool that reads a real Markdown document from a local `data` folder. We run it locally—without Foundry involved—and ask questions about that document. This gives us a concrete way to see the agent select a tool and use its result.

Once the local version works, we upload the same agent to Foundry in three different ways: as a ZIP code package, as a container image, and through the Azure Developer CLI. For each approach, we show where the hosted agent appears in Foundry and test it there. This separates the agent logic from the deployment mechanism: the Python agent stays the same while the packaging and infrastructure change.

The article follows this progression:

1. Configure the project and model settings in `.env`.
2. Create the Python agent and its MCP-style tools.
3. Start the hosted-agent server locally and invoke it with a Responses API client.
4. Upload the tested source code to Foundry as a ZIP package, container image, and azd application.
5. Open and test the hosted agent in Foundry after each deployment.
6. Apply the same deployment and operational ideas to a production release.

The deployment script leaves the version deployed by default. Set `DELETE_AFTER_TEST=true` when you want a disposable validation run.

## The architecture we will implement

The example keeps the architecture deliberately small: a user sends a question to the hosted-agent endpoint, the model decides whether it needs the Markdown-reading tool, and the Python process executes that tool against the bundled `data` folder. The tool result then goes back to the model, which writes the answer:

```text
User -> Hosted agent endpoint -> model chooses read_markdown_file() or query_json_data()
                                 -> Python executes the MCP tool locally
                                 -> model writes the final answer
```

This is the important boundary in the example. The model decides **when** a tool is needed, but your Python code controls **what the tool can access and do**. The same pattern can later be extended to databases, internal APIs, or a real MCP server.

### The Responses protocol and other endpoint shapes

This example uses the **Responses** protocol because it is designed for conversational requests and supports streaming responses. Hosted agents can also expose invocation-style endpoints for non-conversational workloads or WebSocket-based endpoints for interactive, bidirectional scenarios. The protocol is part of the deployment contract: choose the endpoint shape that matches the client that will call the agent.

We will keep the implementation focused on `/responses`. The deployment scripts register that protocol, and `01_invoke_local.py` exercises the same request shape before the code is uploaded to Foundry.

## Prerequisites

- A Foundry project with a chat-capable model deployment.
- Azure CLI installed and authenticated with `az login`.
- Python 3.13 or later.
- **Foundry Project Manager** at project scope to deploy the hosted agent.
- The `azure-ai-projects`, `azure-ai-agentserver-agentframework`, `agent-framework`, `azure-identity`, and `python-dotenv` packages.

## 1. Configure the project and model settings

From this article's directory:

```powershell
python -m venv code\.venv
.\code\.venv\Scripts\Activate.ps1
pip install -r code\requirements.txt
Copy-Item code\.env.example code\.env
```

Edit `code\.env`:

```dotenv
AZURE_AI_PROJECT_ENDPOINT=https://<account>.services.ai.azure.com/api/projects/<project>
MODEL_DEPLOYMENT=<model-deployment-name>
LOCAL_AGENT_BASE_URL=http://127.0.0.1:8088
TEST_PROMPT=Read data/quantum-computing-rag-test.md and summarize how quantum computing differs from classical computing.
```

The hosted process uses `DefaultAzureCredential` locally (via `az login`) and `ManagedIdentityCredential` when Foundry runs it in production. Environment variables are injected by the platform and read directly in the code—no .env file is needed at deployment time.

## 2. Create the Python agent and MCP-style tools

The agent entry point is [`code/00_create_agent.py`](code/00_create_agent.py). The tools are defined in [`code/tools.py`](code/tools.py). The main demonstration tool reads the reusable Part 3 fixture [`code/data/quantum-computing-rag-test.md`](code/data/quantum-computing-rag-test.md). A second tool can search a local JSON data file and filter its records by field. Together, they provide a small, concrete example of how the agent can call code it owns instead of relying only on prompt instructions:

```python
@tool
def read_markdown_file(file_path: str, max_lines: int = 50) -> str:
    """Read a Markdown file from the local filesystem and return its content."""
    # Implementation: read file safely from agent's working directory
    ...

@tool
def query_json_data(data_type: str, query_field: str = None) -> str:
    """Query structured JSON data and return matching records."""
    # Implementation: query product catalog, FAQs, or documentation index
    ...
```

The Microsoft Agent Framework `@tool` decorator converts the function signature and docstring into a tool schema. When the model calls the tool, the Python function executes in the agent process. `ResponsesHostServer(agent).run()` provides the `/responses` HTTP server that Foundry expects.

**00_create_agent.py structure:**

```python
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

client = FoundryChatClient(
    project_endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
    model=os.environ["MODEL_DEPLOYMENT"],
    credential=DefaultAzureCredential(),
)

agent = Agent(
    client=client,
    instructions=INSTRUCTIONS,
    tools=[read_markdown_file, query_json_data],
    default_options={"store": False},
)

set_resilient_tasks_enabled(True)
ResponsesHostServer(agent).run()
```

These tools represent how a hosted agent can:
- Query local knowledge bases or documentation without exposing them through public APIs.
- Access databases or configuration systems with controlled, scoped permissions.
- Orchestrate MCP tools that require authentication or local execution.

## 3. Run and test the agent locally

Start the local server:

```powershell
python code\00_create_agent.py
```

In another terminal, send a Responses API request:

```powershell
python code\01_invoke_local.py
```

This script is a small test client. It reads `LOCAL_AGENT_BASE_URL` and `TEST_PROMPT` from `.env`, creates an OpenAI-compatible client, and sends one `responses.create()` request to the local `/responses` endpoint. With the default settings, it sends this prompt to `http://127.0.0.1:8088/responses`:

```text
Read data/quantum-computing-rag-test.md and summarize how quantum computing differs from classical computing.
```

The `api_key` in this local client is only a placeholder because the local server does not authenticate the request. Nothing is sent to Foundry at this stage; the request is handled entirely by the Python process started by `00_create_agent.py`.

The default prompt asks the agent to read the quantum-computing Markdown fixture and explain it. In the server terminal, you should see a log line from `read_markdown_file()` showing that the tool was called. The response in the client terminal should summarize the document. Try changing `TEST_PROMPT` to ask a different question about the same file, then run the client again. Stop the server with `Ctrl+C` when you are done.

## 4. Package and deploy the agent to Foundry

The local test is complete only when the agent has successfully read the fixture and answered a question about it. We now use that same tested source code to deploy the hosted agent to Foundry. The deployment mechanism changes, but the agent code and local test prompt remain the same. The three deployment patterns are:

### Code package: ZIP with remote build

The first deployment path packages `00_create_agent.py`, `tools.py`, `requirements.txt`, and the `data` folder into a ZIP file. Foundry receives the source package, builds the Python runtime remotely, installs the dependencies, and starts `00_create_agent.py`.

Use this when you want the fastest path from local code to a hosted version and you do not need a custom Docker image.

```powershell
python code\02_deploy_zip.py
```

The script creates the package, uploads it to Foundry, waits for the hosted-agent version to become active, and sends the same Markdown-based smoke-test prompt. When it finishes, copy the agent name and version from the terminal output.

This example uses `dependency_resolution=remote_build`. Foundry receives the source and `requirements.txt`, then installs the dependencies during deployment. That keeps the package small and is convenient for development. A bundled build is another option when you need to ship prebuilt dependencies or reduce reliance on package installation during deployment, at the cost of a larger and more carefully reproducible package.

Open the Foundry portal and go to **Build > Agents**. Open `mcp-knowledge-agent`, select the newly created active version, and use the test/playground experience to send:

```text
Read data/quantum-computing-rag-test.md and explain the difference between a classical bit and a qubit.
```

The deployed agent should answer from the Markdown file included in the ZIP package. If the portal test fails, first confirm that the version is `active`, then inspect the hosted-agent logs for startup or file-packaging errors.

### Container: Docker image in Azure Container Registry

The second deployment path builds a container image locally, pushes it to Azure Container Registry, and registers that image as a hosted-agent version in Foundry. Foundry pulls and runs the image instead of building from a ZIP package.

Use this when you need explicit image versioning, custom system dependencies, or the same container workflow your team already uses in CI/CD.

Before running the script, set the container variables in `.env`, especially `ACR_NAME`. If your registry requires a Foundry private-registry connection, also set `CONTAINER_REGISTRY_CONNECTION_ID`.

```powershell
python code\03_deploy_container.py
```

The script creates this `Dockerfile` if it does not already exist:

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY 00_create_agent.py tools.py ./
COPY data ./data
CMD ["python", "00_create_agent.py"]
```

When the script reports that the version is active, open **Build > Agents** in the Foundry portal and select the agent named by `CONTAINER_AGENT_NAME`. Choose its active version and send the same Markdown question in the test/playground experience. This confirms that Foundry pulled the image, started `00_create_agent.py`, and that the image contains the `data` folder. If it fails, check the ACR image tag, the registry connection, and the hosted-agent logs.

### Azure Developer CLI (azd)

The third deployment path uses Azure Developer CLI as the deployment orchestrator. The script writes an `azure.yaml` file that declares a `host: azure.ai.agent` service, configures an azd environment from `.env`, and runs `azd deploy`.

Use this when you want the hosted-agent deployment to live in an azd workflow, especially if the agent later needs supporting Azure resources or CI/CD deployment.

```powershell
azd auth login
python code\04_deploy_azd.py
```

If this folder has not been initialized against a Foundry project before, set `AZD_PROJECT_ID` in `.env` to the full ARM ID of the Foundry project. The script then runs `azd ai agent init` before `azd deploy`.

After `azd deploy` completes, open **Build > Agents** in the Foundry portal and select the agent named by `AZD_AGENT_NAME`. Open the active version and send the Markdown question in the test/playground experience. The result should match the local test and the ZIP/container deployments. This final check verifies that azd uploaded the same source files and registered the hosted agent in the intended Foundry project.

### Quick comparison

| Pattern | Setup complexity | Ideal for | Versioning |
| --- | --- | --- | --- |
| **Code** | Low | Prototyping, small agents, fast iteration | ZIP per deployment |
| **Container** | Medium | Complex environments, team workflows | Container image tags |
| **Azure Developer CLI** | Medium-high | IaC, multi-environment, CI/CD pipelines | Git + `azure.yaml` |

All three patterns produce a hosted agent running in Foundry Agent Service with the same Responses protocol endpoint. The choice depends on your development workflow and infrastructure requirements.

For each deployment, the validation sequence is the same: confirm the version is `active`, open the agent under **Build > Agents**, ask a question about `data/quantum-computing-rag-test.md`, and inspect the hosted-agent logs if the answer is not returned. The deployment method changes; the agent behavior should not.

Both agent types still require authorization, input validation, monitoring, evaluation, and guardrails. Hosted agents add a code execution boundary and a deployment lifecycle.

## Cleanup

To remove a deployed hosted agent from Foundry, delete the specific version with the Python SDK. The deployed version does not auto-delete; you manage its lifecycle explicitly.

Create a small cleanup script, or run the equivalent code from an authenticated Python session:

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

project = AIProjectClient(
    endpoint="<foundry-project-endpoint>",
    credential=DefaultAzureCredential(),
)

agent_name = "<agent-name>"
agent_version = "<agent-version>"

# Delete only this hosted-agent version.
project.agents.delete_version(
    agent_name=agent_name,
    agent_version=agent_version,
)
print(f"Deleted {agent_name}:{agent_version}")
```

To delete the agent and all of its versions instead:

```python
project.agents.delete(agent_name=agent_name)
print(f"Deleted agent {agent_name} and all versions")
```

The second command is destructive for every version of that agent. In the Foundry portal, you can also delete the agent from **Operate > Assets > Agents**. Use the version-specific delete when you want to clean up a test deployment without removing other versions.

For an azd-managed environment, `azd down` is the broad cleanup command:

```powershell
azd down
```

Use this only when you intend to remove the Azure resources managed by the current azd environment. It is not the safest command for deleting one hosted-agent version, especially when `AZD_PROJECT_ID` points to an existing Foundry project that contains other resources or agents.

The Azure CLI also provides targeted hosted-agent deletion commands. These commands are currently in preview:

```powershell
# Delete one hosted-agent version.
az cognitiveservices agent delete `
  --account-name <foundry-account-name> `
  --project-name <foundry-project-name> `
  --name <agent-name> `
  --agent-version <agent-version>

# Delete all versions for the agent.
az cognitiveservices agent delete `
  --account-name <foundry-account-name> `
  --project-name <foundry-project-name> `
  --name <agent-name>
```

If you only want to stop the running deployment while retaining the version definition, use `az cognitiveservices agent delete-deployment` with the same account, project, agent name, and `--agent-version` values.

For production deployments, keep an active version only after reviewing its identity, permissions, traffic routing, logs, cost, and the MCP tools it accesses.

## Full sample code

- [`.env.example`](code/.env.example)
- [`requirements.txt`](code/requirements.txt)
- [`00_create_agent.py`](code/00_create_agent.py)
- [`tools.py`](code/tools.py)
- [`01_invoke_local.py`](code/01_invoke_local.py)
- [`02_deploy_zip.py`](code/02_deploy_zip.py)
- [`03_deploy_container.py`](code/03_deploy_container.py)
- [`04_deploy_azd.py`](code/04_deploy_azd.py)
- [`data/quantum-computing-rag-test.md`](code/data/quantum-computing-rag-test.md)

Next: [Part 9 - Multi-agent orchestration](/blog/microsoft-foundry/part9-multi-agent-orchestration), [Part 11 - From notebook to production](/blog/microsoft-foundry/part11-from-notebook-to-production), and [Part 12 - Agent Insights](/blog/microsoft-foundry/part12-agent-insights).

---

Sources: [Deploy a hosted agent from source code](https://learn.microsoft.com/azure/foundry/agents/how-to/deploy-hosted-agent-code), [Quickstart: Deploy your first hosted agent](https://learn.microsoft.com/azure/foundry/agents/quickstarts/quickstart-hosted-agent), [Model Context Protocol documentation](https://spec.modelcontextprotocol.io/), [Hosted Agents workshop](https://github.com/LauraVerghote/Hosted-agents-workshop/tree/main/lab-1-build-hosted-agent).
