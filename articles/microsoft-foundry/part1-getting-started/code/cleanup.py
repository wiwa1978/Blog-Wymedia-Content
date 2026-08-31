"""
Cleanup - delete the project(s) and the Foundry resource created in
this walkthrough.
"""
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient

load_dotenv()
subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
resource_group_name = os.environ["AZURE_RESOURCE_GROUP"]
foundry_resource_name = os.environ["AZURE_FOUNDRY_RESOURCE_NAME"]

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
