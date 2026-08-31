---
title: "Getting Started"
excerpt: "A practical Python walkthrough for creating Microsoft Foundry resources and projects, deploying a model, and building your first agent."
slug: microsoft-foundry/part1-getting-started
artifactPath: "Microsoft Foundry/part1-getting-started"
tags: ["azure", "ai-foundry", "python", "sdk", "getting-started"]
series: {"slug":"microsoft-foundry","title":"Microsoft Foundry","part":1}
publishAt: "2026-07-01T07:00:00.000Z"
---
# Part 1 - Getting Started with the Microsoft Foundry SDK

Microsoft Foundry (formerly Azure AI Foundry) gives you one place to create AI resources, deploy models, and build agents. This post walks through the **Python SDK** end to end: setting up an isolated environment, creating the underlying Azure resource and project, inspecting what got created, deploying/using a model, and building your first agent — each step with a small, runnable snippet that prints out what it just did.

## Prerequisites

- An Azure subscription with permission to create resources (e.g. **Foundry Account Owner**/**Owner** on the target resource group).
- [Python 3.9+](https://www.python.org/downloads/) and the [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli).
- You're signed in to Azure from your terminal:

```bash
az login
```

## Step 1 — Create a virtual environment

Keep SDK versions isolated per project — Foundry's "classic" and "new" SDKs use different, incompatible package versions.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

Install the packages you'll need for this walkthrough:

```bash
pip install "azure-ai-projects>=2.3.0" azure-identity "azure-mgmt-cognitiveservices~=13.7.0" python-dotenv
```

## Step 2 — Verify authentication

Before creating anything, confirm `DefaultAzureCredential` (which picks up your `az login` session) actually works.

```python
# 01_verify_auth.py
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient

subscription_id = "<your-subscription-id>"

credential = DefaultAzureCredential()
client = CognitiveServicesManagementClient(credential, subscription_id)

print("✓ Authentication successful — ready to create Foundry resources.")
```

## Step 3 — Create the Foundry resource

Everything in Foundry lives on top of a **Foundry resource** (an Azure Cognitive Services account of kind `AIServices`). This is the parent resource that projects, model deployments, and connections attach to.

```python
# 02_create_foundry_resource.py
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient

subscription_id = "<your-subscription-id>"
resource_group_name = "my-foundry-rg"
foundry_resource_name = "my-foundry-resource"      # must be globally unique
location = "eastus"

client = CognitiveServicesManagementClient(
    credential=DefaultAzureCredential(),
    subscription_id=subscription_id,
    api_version="2025-04-01-preview",
)

resource = client.accounts.begin_create(
    resource_group_name=resource_group_name,
    account_name=foundry_resource_name,
    account={
        "location": location,
        "kind": "AIServices",
        "sku": {"name": "S0"},
        "identity": {"type": "SystemAssigned"},
        "properties": {
            "allowProjectManagement": True,
            "customSubDomainName": foundry_resource_name,
        },
    },
)
result = resource.result()

print(f"✓ Foundry resource created: {result.name}")
print(f"  Location:          {result.location}")
print(f"  Provisioning state: {result.properties.provisioning_state}")
print(f"  Endpoint:           {result.properties.endpoint}")
```

> 💡 If you'd rather not wait for resource creation to finish before scripting further, note that `.begin_create()` returns a long-running-operation poller — `.result()` blocks until it's done.

## Step 4 — Create a project on the resource

A **project** is your workspace inside the Foundry resource — where agents, evaluations, and files live.

```python
# 03_create_project.py
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient

subscription_id = "<your-subscription-id>"
resource_group_name = "my-foundry-rg"
foundry_resource_name = "my-foundry-resource"
foundry_project_name = "my-foundry-project"
location = "eastus"

client = CognitiveServicesManagementClient(
    credential=DefaultAzureCredential(),
    subscription_id=subscription_id,
    api_version="2025-04-01-preview",
)

project = client.projects.begin_create(
    resource_group_name=resource_group_name,
    account_name=foundry_resource_name,
    project_name=foundry_project_name,
    project={
        "location": location,
        "identity": {"type": "SystemAssigned"},
        "properties": {},
    },
).result()

print(f"✓ Project created: {project.name}")
print(f"  Location: {project.location}")
```

You can add more projects to the same resource later the same way — handy for letting a team share one set of deployments/connections while keeping separate workspaces.

## Step 5 — Confirm the project exists

A quick read-back so you can see exactly what Azure has on record for your project.

```python
# 04_get_project.py
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient

subscription_id = "<your-subscription-id>"
resource_group_name = "my-foundry-rg"
foundry_resource_name = "my-foundry-resource"
foundry_project_name = "my-foundry-project"

client = CognitiveServicesManagementClient(
    credential=DefaultAzureCredential(),
    subscription_id=subscription_id,
    api_version="2025-04-01-preview",
)

project = client.projects.get(
    resource_group_name=resource_group_name,
    account_name=foundry_resource_name,
    project_name=foundry_project_name,
)

print(f"Project name:   {project.name}")
print(f"Location:       {project.location}")
print(f"Provisioning:   {project.properties.provisioning_state}")
```

## Step 6 — Deploy a model

Deployments are a management-plane resource too — the same `CognitiveServicesManagementClient` you used to create the resource and project also creates model deployments, via `client.deployments.begin_create_or_update()`.

```python
# 05_deploy_model.py
import os
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
from azure.mgmt.cognitiveservices.models import Deployment, DeploymentProperties, DeploymentModel, Sku

subscription_id = "<your-subscription-id>"
resource_group_name = "my-foundry-rg"
foundry_resource_name = "my-foundry-resource"
MODEL_DEPLOYMENT = os.getenv("MODEL_DEPLOYMENT", "gpt-5.1-mini")
MODEL_VERSION = os.getenv("MODEL_VERSION", "2025-04-14")
MODEL_SKU_NAME = os.getenv("MODEL_SKU_NAME", "GlobalStandard")
MODEL_SKU_CAPACITY = int(os.getenv("MODEL_SKU_CAPACITY", "10"))

client = CognitiveServicesManagementClient(
    credential=DefaultAzureCredential(),
    subscription_id=subscription_id,
    api_version="2025-04-01-preview",
)

deployment = client.deployments.begin_create_or_update(
    resource_group_name=resource_group_name,
    account_name=foundry_resource_name,
    deployment_name=MODEL_DEPLOYMENT,
    deployment=Deployment(
        sku=Sku(name=MODEL_SKU_NAME, capacity=MODEL_SKU_CAPACITY),
        properties=DeploymentProperties(
            model=DeploymentModel(format="OpenAI", name=MODEL_DEPLOYMENT, version=MODEL_VERSION),
        ),
    ),
).result()

print(f"✓ Model deployed: {deployment.name}")
print(f"  Model:              {deployment.properties.model.name} ({deployment.properties.model.version})")
print(f"  SKU:                {deployment.sku.name} x{deployment.sku.capacity}")
print(f"  Provisioning state: {deployment.properties.provisioning_state}")
```

> 💡 Same idea as CLI's `az cognitiveservices account deployment create` — `sku.name` is the capacity type (`GlobalStandard`, `Standard`, `DataZoneStandard`, ...) and `sku.capacity` is the throughput unit count. `begin_create_or_update()` is a long-running operation, so `.result()` blocks until the deployment is ready.

## Step 7 — List what's deployed and connected

Now switch to the **`AIProjectClient`** (`azure-ai-projects`) — the client for working *inside* a project: models, connections, agents, evaluations, files, and more.

> ⚠️ **First time hitting the data plane?** If you created your resource/project via the SDK or CLI (as in Steps 3-4) rather than the Foundry portal UI, your user identity is **not** automatically granted data-plane access — you'll get `PermissionDenied: Principal does not have access to API/Operation.` Fix it by assigning yourself the **Foundry User** role (previously named **Azure AI User** — some tenants may still show the old name) on the Foundry resource:
>
> ```bash
> az role assignment create \
>     --assignee "<your-user-or-object-id>" \
>     --role "Foundry User" \
>     --scope "/subscriptions/<subscription-id>/resourceGroups/my-foundry-rg/providers/Microsoft.CognitiveServices/accounts/my-foundry-resource"
> ```
>
> Get `<your-user-or-object-id>` by running `az ad signed-in-user show --query id -o tsv` (this is your Entra object ID — works for the `--assignee` flag regardless of whether you signed in with a user account or a service principal). Role assignments can take a minute or two to propagate — retry after a short wait if you still see the error.

```python
# 06_inspect_project.py
import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

PROJECT_ENDPOINT = os.getenv(
    "AZURE_AI_PROJECT_ENDPOINT",
    "https://my-foundry-resource.services.ai.azure.com/api/projects/my-foundry-project",
)

with (
    DefaultAzureCredential() as credential,
    AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential) as project_client,
):
    print("Deployed models:")
    for deployment in project_client.deployments.list():
        print(f"  - {deployment.name} ({deployment.model_publisher}/{deployment.model_name})")

    print("Connections:")
    for connection in project_client.connections.list():
        print(f"  - {connection.name} ({connection.type})")
```

## Step 8 — Chat with a model

This is the core building block of any AI app: send input, get a response.

```python
# 07_chat.py
import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "your_project_endpoint")
MODEL_DEPLOYMENT = os.getenv("MODEL_DEPLOYMENT", "gpt-5.1-mini")

project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())
openai = project.get_openai_client()

response = openai.responses.create(
    model=MODEL_DEPLOYMENT,
    input="What is the size of France in square miles?",
)

print(f"Model used:      {MODEL_DEPLOYMENT}")
print(f"Response output: {response.output_text}")
```

## Step 9 — Create your first agent

An agent packages a model + instructions into a reusable, versioned identity so you don't have to repeat the system prompt every call.

```python
# 08_create_agent.py
import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "your_project_endpoint")
AGENT_NAME = "MyFirstAgent"

project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())

agent = project.agents.create_version(
    agent_name=AGENT_NAME,
    definition=PromptAgentDefinition(
        model="gpt-5.1-mini",
        instructions="You are a helpful assistant that answers general questions.",
    ),
)

print(f"✓ Agent created")
print(f"  Name:    {agent.name}")
print(f"  ID:      {agent.id}")
print(f"  Version: {agent.version}")
```

## Putting it all together

A single script that goes from an authenticated session to a running chat call — useful as a smoke test after creating a new resource.

```python
# foundry_quickstart.py
import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

PROJECT_ENDPOINT = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT = os.environ.get("MODEL_DEPLOYMENT", "gpt-5.1-mini")

with (
    DefaultAzureCredential() as credential,
    AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential) as project_client,
):
    print("== Deployed models ==")
    for d in project_client.deployments.list():
        print(f"  - {d.name}")

    print("\n== Chat test ==")
    openai_client = project_client.get_openai_client()
    response = openai_client.responses.create(
        model=MODEL_DEPLOYMENT,
        input="In one sentence, what is Microsoft Foundry?",
    )
    print(response.output_text)
```

Run it:

```bash
set AZURE_AI_PROJECT_ENDPOINT=https://my-foundry-resource.services.ai.azure.com/api/projects/my-foundry-project
python foundry_quickstart.py
```

## Cleaning up

Delete the project (and everything under it, if you want) when you're done experimenting:

```python
# cleanup.py
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient

subscription_id = "<your-subscription-id>"
resource_group_name = "my-foundry-rg"
foundry_resource_name = "my-foundry-resource"

client = CognitiveServicesManagementClient(
    credential=DefaultAzureCredential(), subscription_id=subscription_id
)

for project in client.projects.list(resource_group_name, foundry_resource_name):
    name = project.name.split("/")[-1]
    print(f"Deleting project: {name}")
    client.projects.begin_delete(resource_group_name, foundry_resource_name, project_name=name).wait()

print(f"Deleting resource: {foundry_resource_name}")
client.accounts.begin_delete(resource_group_name, foundry_resource_name).wait()
print("✓ Cleanup complete.")
```

Or, if you spun up a dedicated resource group just for this, simplest is:

```bash
az group delete --name my-foundry-rg --yes --no-wait
```

## What to try next

- **Add tools to your agent** — Azure AI Search, Bing Grounding, Code Interpreter, or a custom Function Tool.
- **Have a multi-turn conversation** by passing `previous_response_id` between `responses.create()` calls.
- **Add multiple projects** to one Foundry resource so a team shares deployments/connections but keeps separate workspaces.
- **Try instant access models** (skip the deployment step entirely) by creating your project in `westus3`.
- **Wire in evaluations** on your agent's responses using the `.evaluation_rules` / `.beta.evaluators` operations.

## Why this matters

Foundry separates the *management-plane* concern (the resource and project — created once, rarely changed) from the *data-plane* concern (chatting with models and running agents — happening constantly, at scale). Once you've got the resource and project created, the day-to-day `AIProjectClient` code stays exactly the same regardless of which model, agent, or tool you're using underneath — which is what makes it easy to swap models or add capabilities without rewriting your application.

---

## Full Sample Code

Every snippet in this post is available as a standalone, runnable script in the [`code/`](code/) folder — numbered to match the steps above, plus the combined quickstart and cleanup scripts:

- [`01_verify_auth.py`](code/01_verify_auth.py)
- [`02_create_foundry_resource.py`](code/02_create_foundry_resource.py)
- [`03_create_project.py`](code/03_create_project.py)
- [`04_get_project.py`](code/04_get_project.py)
- [`05_deploy_model.py`](code/05_deploy_model.py)
- [`06_inspect_project.py`](code/06_inspect_project.py)
- [`07_chat.py`](code/07_chat.py)
- [`08_create_agent.py`](code/08_create_agent.py)
- [`full_example.py`](code/full_example.py)
- [`cleanup.py`](code/cleanup.py)

See [`code/README.md`](code/README.md) for setup and run instructions. Copy [`code/.env.example`](code/.env.example) to `.env` and fill in your values before running any script.

---

*Sources: [Microsoft Foundry documentation](https://learn.microsoft.com/azure/foundry/), [Azure AI Projects client library (Python)](https://learn.microsoft.com/python/api/overview/azure/ai-projects-readme?view=azure-python), [Create a project for Microsoft Foundry](https://learn.microsoft.com/azure/foundry/how-to/create-projects), [Quickstart: Set up Microsoft Foundry resources](https://learn.microsoft.com/azure/foundry/tutorials/quickstart-create-foundry-resources), [Quickstart: Get started with Microsoft Foundry SDK](https://learn.microsoft.com/azure/foundry/quickstarts/get-started-code).*
