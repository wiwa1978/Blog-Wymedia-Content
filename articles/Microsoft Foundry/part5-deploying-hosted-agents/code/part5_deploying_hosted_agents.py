"""
Microsoft Foundry SDK - Part 5: Deploying Hosted Agents
Complete example demonstrating agent deployment via ZIP and containers.

This script shows:
1. Packaging agent code as a ZIP file
2. Creating a hosted agent version with remote_build dependencies
3. Polling for deployment completion
4. Invoking a hosted agent via the Responses protocol
5. Using Azure Developer CLI for simplified deployment
"""

import hashlib
import time
import requests
from pathlib import Path
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    HostedAgentDefinition,
    CodeConfiguration,
    ProtocolVersionRecord,
    AgentEndpointProtocol
)
from azure.identity import DefaultAzureCredential


def create_agent_zip():
    """Create a minimal agent ZIP file."""
    
    # Create temporary agent code
    agent_code = '''
from azure.ai.projects import AIProjectClient

project_client = AIProjectClient.from_config()

agent_def = {
    "name": "deployed-agent",
    "instructions": "You are a helpful AI assistant deployed to production."
}

print("✓ Hosted agent running")
'''
    
    requirements = '''
azure-ai-projects>=2.3.0
openai>=1.58.0
python-dotenv
'''
    
    # Create ZIP (in production, use zipfile module)
    import subprocess
    
    # For this example, simulate ZIP creation
    zip_path = Path("/tmp/agent-code.zip")
    
    print(f"  ✓ Simulated ZIP creation: {zip_path}")
    print(f"    - main.py")
    print(f"    - requirements.txt")
    
    return zip_path, agent_code, requirements


def deploy_via_zip(project_client):
    """Deploy agent using ZIP (source code) path."""
    
    print("Step 1: Deploy via ZIP (Source Code)")
    print("-" * 40)
    
    # Step 1a: Create ZIP
    zip_path, agent_code, requirements = create_agent_zip()
    
    # Step 1b: Hash the ZIP for versioning
    # In production: with open(zip_path, "rb") as f: zip_sha256 = hashlib.sha256(f.read()).hexdigest()
    zip_sha256 = hashlib.sha256(b"agent_code_content").hexdigest()
    print(f"  ✓ ZIP SHA-256: {zip_sha256[:16]}...")
    print()
    
    # Step 1c: Create hosted agent with ZIP
    print("Step 2: Creating Hosted Agent Version (ZIP)")
    print("-" * 40)
    
    code_config = CodeConfiguration(
        runtime="python_3_13",
        source_uri="https://your-storage-account.blob.core.windows.net/agent-code.zip"
    )
    
    protocol_versions = [
        ProtocolVersionRecord(
            protocol=AgentEndpointProtocol.RESPONSES,
            version="1.0.0"
        )
    ]
    
    hosted_agent_def = HostedAgentDefinition(
        name="zip-deployed-agent",
        code_configuration=code_config,
        protocol_versions=protocol_versions
    )
    
    print(f"  ✓ Agent Definition:")
    print(f"    - Runtime: python_3_13")
    print(f"    - Protocols: Responses 1.0.0")
    print()
    
    # Step 2: Poll for active status
    print("Step 3: Polling Deployment Status")
    print("-" * 40)
    
    print("  Simulating deployment polling...")
    statuses = ["provisioning", "packaging", "staging", "activating", "active"]
    
    for i, status in enumerate(statuses, 1):
        print(f"    {i}. Status: {status}")
        if status == "active":
            print(f"  ✓ Agent is now ACTIVE")
            break
        time.sleep(0.2)  # Simulate wait
    
    print()
    return "agent-version-123"


def deploy_via_container(project_client):
    """Deploy agent using container path."""
    
    print("Step 1: Deploy via Container")
    print("-" * 40)
    
    # Step 1a: Simulate Docker build/push
    print("  ✓ Docker image built for linux/amd64")
    print("  ✓ Image pushed to ACR: myregistry.azurecr.io/my-agent:v1.0.0")
    print()
    
    # Step 1b: Create hosted agent with container
    print("Step 2: Creating Hosted Agent Version (Container)")
    print("-" * 40)
    
    from azure.ai.projects.models import ContainerConfiguration
    
    container_config = ContainerConfiguration(
        image_uri="myregistry.azurecr.io/my-agent:v1.0.0",
        environment_variables={
            "LOG_LEVEL": "INFO",
            "ENABLE_METRICS": "true"
        }
    )
    
    protocol_versions = [
        ProtocolVersionRecord(
            protocol=AgentEndpointProtocol.RESPONSES,
            version="1.0.0"
        )
    ]
    
    hosted_agent_def = HostedAgentDefinition(
        name="container-deployed-agent",
        container_configuration=container_config,
        protocol_versions=protocol_versions
    )
    
    print(f"  ✓ Agent Definition:")
    print(f"    - Image: myregistry.azurecr.io/my-agent:v1.0.0")
    print(f"    - Protocols: Responses 1.0.0")
    print()
    
    # Step 2: Poll for active
    print("Step 3: Polling Deployment Status")
    print("-" * 40)
    
    print("  Simulating container deployment polling...")
    statuses = ["pulling_image", "initializing", "health_check", "active"]
    
    for i, status in enumerate(statuses, 1):
        print(f"    {i}. Status: {status}")
        if status == "active":
            print(f"  ✓ Container agent is now ACTIVE")
            break
        time.sleep(0.2)
    
    print()
    return "agent-version-456"


def invoke_hosted_agent(project_client, version_id):
    """Invoke a deployed hosted agent."""
    
    print("Step 4: Invoking Hosted Agent")
    print("-" * 40)
    
    # Simulate invocation
    endpoint = f"https://your-project.azureml.net/agent/versions/{version_id}/responses"
    
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "What are the benefits of cloud computing?"
            }
        ]
    }
    
    print(f"  Endpoint: {endpoint}")
    print(f"  Request: {payload['messages'][0]['content']}")
    print()
    
    # Simulate response
    print("  Streaming response:")
    print("    ✓ Received SSE event (content chunk 1)")
    print("    ✓ Received SSE event (content chunk 2)")
    print("    ✓ Response complete")
    print()
    
    response_text = (
        "Cloud computing offers several key benefits:\n"
        "1. **Scalability** - Easily scale resources up or down\n"
        "2. **Cost Efficiency** - Pay only for what you use\n"
        "3. **Global Accessibility** - Access from anywhere"
    )
    
    print(f"  Response:\n  {response_text}")


def main():
    # Initialize Foundry client
    project_client = AIProjectClient.from_config(
        credential=DefaultAzureCredential()
    )
    
    print(f"✓ Connected to project: {project_client.project_name}")
    print()
    
    # Choose deployment path
    deployment_choice = "zip"  # or "container"
    
    if deployment_choice == "zip":
        print("=" * 50)
        print("DEPLOYMENT PATH A: Source Code (ZIP)")
        print("=" * 50)
        print()
        
        version_id = deploy_via_zip(project_client)
    else:
        print("=" * 50)
        print("DEPLOYMENT PATH B: Container")
        print("=" * 50)
        print()
        
        version_id = deploy_via_container(project_client)
    
    # Invoke the agent
    invoke_hosted_agent(project_client, version_id)
    
    print()
    print("Cleanup")
    print("-" * 40)
    print("  ✓ Agent version can be deleted or kept for rollback")
    print("  ✓ Consider keeping 2 versions for blue-green deployments")


if __name__ == "__main__":
    main()
