"""
Step 6 - Deploy a model.

Model deployments are a management-plane resource on the Foundry resource
(Cognitive Services account) — the same CognitiveServicesManagementClient
used to create the resource and project also creates deployments, via
`client.deployments.begin_create_or_update()`.
"""
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
from azure.mgmt.cognitiveservices.models import Deployment, DeploymentProperties, DeploymentModel, Sku

load_dotenv()
subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
resource_group_name = os.environ["AZURE_RESOURCE_GROUP"]
foundry_resource_name = os.environ["AZURE_FOUNDRY_RESOURCE_NAME"]
deployment_name = os.getenv("MODEL_DEPLOYMENT", "gpt-5.1-mini")
model_version = os.getenv("MODEL_VERSION", "2025-04-14")
sku_name = os.getenv("MODEL_SKU_NAME", "GlobalStandard")
sku_capacity = int(os.getenv("MODEL_SKU_CAPACITY", "10"))

client = CognitiveServicesManagementClient(
    credential=DefaultAzureCredential(),
    subscription_id=subscription_id,
    api_version="2025-04-01-preview",
)

deployment = client.deployments.begin_create_or_update(
    resource_group_name=resource_group_name,
    account_name=foundry_resource_name,
    deployment_name=deployment_name,
    deployment=Deployment(
        sku=Sku(name=sku_name, capacity=sku_capacity),
        properties=DeploymentProperties(
            model=DeploymentModel(
                format="OpenAI",
                name=deployment_name,
                version=model_version,
            ),
        ),
    ),
).result()

print(f"✓ Model deployed: {deployment.name}")
print(f"  Model:              {deployment.properties.model.name} ({deployment.properties.model.version})")
print(f"  SKU:                {deployment.sku.name} x{deployment.sku.capacity}")
print(f"  Provisioning state: {deployment.properties.provisioning_state}")
