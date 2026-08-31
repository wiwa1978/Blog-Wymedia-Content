"""
Step 5 - Confirm the project exists.

A quick read-back so you can see exactly what Azure has on record for
your project.
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
