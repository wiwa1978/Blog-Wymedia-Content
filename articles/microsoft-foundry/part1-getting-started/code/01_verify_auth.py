"""
Step 2 - Verify authentication.

Confirms DefaultAzureCredential (which picks up your `az login` session)
actually works before you try to create any Foundry resources.
"""
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient

load_dotenv()
subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]

credential = DefaultAzureCredential()
client = CognitiveServicesManagementClient(credential, subscription_id)

print("✓ Authentication successful — ready to create Foundry resources.")
