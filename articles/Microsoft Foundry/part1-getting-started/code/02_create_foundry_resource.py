"""
Step 3 - Create the Foundry resource.

Everything in Foundry lives on top of a Foundry resource (an Azure
Cognitive Services account of kind `AIServices`). This is the parent
resource that projects, model deployments, and connections attach to.
"""
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient

load_dotenv()
subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
resource_group_name = os.environ["AZURE_RESOURCE_GROUP"]
foundry_resource_name = os.environ["AZURE_FOUNDRY_RESOURCE_NAME"]      # must be globally unique
location = os.getenv("AZURE_LOCATION", "eastus")

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
