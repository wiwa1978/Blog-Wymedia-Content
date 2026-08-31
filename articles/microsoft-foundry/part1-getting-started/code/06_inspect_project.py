"""
Step 7 - List what's deployed and connected.

Switches to the AIProjectClient (azure-ai-projects) — the client for
working *inside* a project: models, connections, agents, evaluations,
files, and more.

Before running: deploy a model with the Azure CLI (see Step 6 in the
article), then set AZURE_AI_PROJECT_ENDPOINT to your project's endpoint.
"""
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

load_dotenv()
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
