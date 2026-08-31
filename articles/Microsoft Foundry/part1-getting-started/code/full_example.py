"""
Full example - a single script that goes from an authenticated session
to a running chat call. Combines every step of the article: creating the
Foundry resource + project (Steps 3-5), deploying a model via the SDK
(Step 6), then inspecting/chat/agent-creation (Steps 7-9) in one place.

Run:
    python full_example.py
(reads settings from .env — see .env.example)
"""
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
from azure.mgmt.cognitiveservices.models import Deployment, DeploymentProperties, DeploymentModel, Sku
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

load_dotenv()
SUBSCRIPTION_ID = os.environ["AZURE_SUBSCRIPTION_ID"]
RESOURCE_GROUP = os.environ["AZURE_RESOURCE_GROUP"]
FOUNDRY_RESOURCE_NAME = os.environ["AZURE_FOUNDRY_RESOURCE_NAME"]
PROJECT_ENDPOINT = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT = os.environ.get("MODEL_DEPLOYMENT", "gpt-5.1-mini")
MODEL_VERSION = os.environ.get("MODEL_VERSION", "2025-04-14")
MODEL_SKU_NAME = os.environ.get("MODEL_SKU_NAME", "GlobalStandard")
MODEL_SKU_CAPACITY = int(os.environ.get("MODEL_SKU_CAPACITY", "10"))

credential = DefaultAzureCredential()

print("== Deploy model (management plane) ==")
mgmt_client = CognitiveServicesManagementClient(
    credential=credential, subscription_id=SUBSCRIPTION_ID, api_version="2025-04-01-preview"
)
deployment = mgmt_client.deployments.begin_create_or_update(
    resource_group_name=RESOURCE_GROUP,
    account_name=FOUNDRY_RESOURCE_NAME,
    deployment_name=MODEL_DEPLOYMENT,
    deployment=Deployment(
        sku=Sku(name=MODEL_SKU_NAME, capacity=MODEL_SKU_CAPACITY),
        properties=DeploymentProperties(
            model=DeploymentModel(format="OpenAI", name=MODEL_DEPLOYMENT, version=MODEL_VERSION)
        ),
    ),
).result()
print(f"  ✓ {deployment.name} ({deployment.properties.provisioning_state})")

with AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential) as project_client:
    print("\n== Deployed models ==")
    for d in project_client.deployments.list():
        print(f"  - {d.name}")

    print("\n== Chat test ==")
    openai_client = project_client.get_openai_client()
    response = openai_client.responses.create(
        model=MODEL_DEPLOYMENT,
        input="In one sentence, what is Microsoft Foundry?",
    )
    print(response.output_text)

    print("\n== Create an agent ==")
    agent = project_client.agents.create_version(
        agent_name="MyFirstAgent",
        definition=PromptAgentDefinition(
            model=MODEL_DEPLOYMENT,
            instructions="You are a helpful assistant that answers general questions.",
        ),
    )
    print(f"✓ Agent created: {agent.name} (version {agent.version})")

