"""
Step 4 - Create a project on the resource.

A project is your workspace inside the Foundry resource — where agents,
evaluations, and files live.
"""
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient

load_dotenv()
subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
resource_group_name = os.environ["AZURE_RESOURCE_GROUP"]
foundry_resource_name = os.environ["AZURE_FOUNDRY_RESOURCE_NAME"]
foundry_project_name = os.environ["AZURE_FOUNDRY_PROJECT_NAME"]
location = os.getenv("AZURE_LOCATION", "eastus")

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
