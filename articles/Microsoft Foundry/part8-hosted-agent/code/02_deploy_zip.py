#!/usr/bin/env python3
"""
Deploy a hosted agent via code package (ZIP + remote build).

This script packages the agent source code and requirements.txt into a ZIP,
uploads it to Foundry Agent Service, and waits for the deployment to complete.

Foundry builds a container with Python runtime, installs dependencies from
requirements.txt, and runs 00_create_agent.py as the entry point.

Usage:
    python 02_deploy_zip.py

Environment variables (from .env):
    AZURE_AI_PROJECT_ENDPOINT - Foundry project endpoint URL
    MODEL_DEPLOYMENT - Model deployment name
    AZURE_SUBSCRIPTION_ID - Azure subscription ID (optional, auto-detected from endpoint)

Exit codes:
    0 - Deployment successful
    1 - Configuration error
    2 - Deployment failed
    3 - Timeout waiting for deployment
"""
import os
import hashlib
import sys
import time
import zipfile
import tempfile
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    CodeConfiguration,
    HostedAgentDefinition,
    ProtocolVersionRecord,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def load_config():
    """Load configuration from environment and .env file."""
    load_dotenv()

    config = {
        "project_endpoint": os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
        "model_deployment": os.getenv("MODEL_DEPLOYMENT"),
        "agent_name": os.getenv("ZIP_AGENT_NAME", "mcp-knowledge-agent"),
        "timeout_seconds": 300,  # 5 minutes max wait
    }

    if not config["project_endpoint"]:
        print("❌ Error: AZURE_AI_PROJECT_ENDPOINT not set in .env")
        sys.exit(1)

    if not config["model_deployment"]:
        print("❌ Error: MODEL_DEPLOYMENT not set in .env")
        sys.exit(1)

    return config


def create_deployment_package(code_dir: Path) -> Path:
    """
    Create a ZIP file containing agent source code and requirements.txt.

    Args:
        code_dir: Directory containing the agent source, requirements.txt, and data fixtures.

    Returns:
        Path to the created ZIP file
    """
    print("📦 Creating deployment package...")

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
        zip_path = Path(temp_zip.name)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add Python source files
        for py_file in ["00_create_agent.py", "tools.py", "requirements.txt"]:
            file_path = code_dir / py_file
            if file_path.exists():
                zf.write(file_path, arcname=py_file)
                print(f"  ✓ Added {py_file}")
            else:
                print(f"  ⚠️  Warning: {py_file} not found")

        data_dir = code_dir / "data"
        if data_dir.exists():
            for data_file in data_dir.rglob("*"):
                if data_file.is_file():
                    zf.write(data_file, arcname=data_file.relative_to(code_dir))
                    print(f"  ✓ Added {data_file.relative_to(code_dir)}")

    print(f"✅ Package created: {zip_path} ({zip_path.stat().st_size:,} bytes)")
    return zip_path


def create_project_client(config: dict) -> AIProjectClient:
    """Create an authenticated Foundry project client."""
    return AIProjectClient(
        endpoint=config["project_endpoint"],
        credential=DefaultAzureCredential(),
    )


def get_field(value, field_name: str, default=None):
    """Read SDK models that may expose values as attributes or dict keys."""
    if isinstance(value, dict):
        return value.get(field_name, default)
    return getattr(value, field_name, default)


def deploy_hosted_agent(config: dict, zip_path: Path):
    """
    Upload the ZIP package to Foundry and create a hosted agent version.

    Args:
        config: Configuration dictionary
        zip_path: Path to the deployment ZIP file

    Returns:
        Tuple of project client and created version
    """
    print(f"\n🚀 Deploying to Foundry ({config['agent_name']})...")

    client = create_project_client(config)

    try:
        print("  → Uploading code package...")
        code_zip_bytes = zip_path.read_bytes()
        code_zip_sha256 = hashlib.sha256(code_zip_bytes).hexdigest()

        with open(zip_path, "rb") as f:
            agent_name = config["agent_name"]

            created = client.agents.create_version_from_code(
                agent_name=agent_name,
                definition=HostedAgentDefinition(
                    cpu="1",
                    memory="2Gi",
                    code_configuration=CodeConfiguration(
                        runtime="python_3_13",
                        entry_point=["python", "00_create_agent.py"],
                        dependency_resolution="remote_build",
                    ),
                    protocol_versions=[
                        ProtocolVersionRecord(protocol="responses", version="2.0.0")
                    ],
                    environment_variables={
                        "AZURE_AI_PROJECT_ENDPOINT": config["project_endpoint"],
                        "MODEL_DEPLOYMENT": config["model_deployment"],
                    },
                ),
                code=f,
                code_zip_sha256=code_zip_sha256,
                description="MCP tools demonstration agent",
            )

            version = get_field(created, "version", "unknown")
            print(f"✅ Agent '{agent_name}' version created")
            print(f"   Version: {version}")

            return client, version

    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        sys.exit(2)


def wait_for_deployment(client: AIProjectClient, config: dict, version: str) -> bool:
    """
    Poll the hosted agent status until it becomes active.

    Args:
        config: Configuration dictionary
        version: Version of the deployed agent

    Returns:
        True if deployment succeeded, False on timeout
    """
    print(f"\n⏳ Waiting for agent to become active (timeout: {config['timeout_seconds']}s)...")

    start_time = time.time()
    poll_interval = 5  # Check every 5 seconds

    while time.time() - start_time < config["timeout_seconds"]:
        try:
            response = client.agents.get_version(
                agent_name=config["agent_name"],
                agent_version=version,
            )
            status = get_field(response, "status", "unknown")

            if status == "active":
                print(f"✅ Agent is active!")
                return True

            print(f"  → Status: {status}... (elapsed: {int(time.time() - start_time)}s)")
            time.sleep(poll_interval)

        except Exception as e:
            print(f"  ⚠️  Query failed: {e}. Retrying...")
            time.sleep(poll_interval)

    print(f"❌ Deployment timeout after {config['timeout_seconds']}s")
    return False


def test_deployment(client: AIProjectClient, config: dict) -> None:
    """
    Send a test request to the deployed agent via the Responses API.

    Args:
        config: Configuration dictionary
        config: Configuration dictionary
    """
    print(f"\n🧪 Testing deployed agent...")

    try:
        openai_client = client.get_openai_client(agent_name=config["agent_name"])
        
        test_prompt = os.getenv(
            "TEST_PROMPT",
            "Read data/quantum-computing-rag-test.md and summarize how quantum computing differs from classical computing.",
        )
        print(f"  → Sending: '{test_prompt}'")

        response = openai_client.responses.create(input=test_prompt)

        print(f"✅ Response received:")
        print(f"   {response}")

    except Exception as e:
        print(f"⚠️  Test invocation failed: {e}")
        print("   (The agent may not be fully initialized yet. Try again in a moment.)")


def main():
    """Main deployment workflow."""
    print("=" * 70)
    print("Deploy Hosted Agent via Code Package (ZIP + Remote Build)")
    print("=" * 70)

    config = load_config()
    code_dir = Path(__file__).parent

    zip_path = create_deployment_package(code_dir)

    try:
        client, version = deploy_hosted_agent(config, zip_path)

        if wait_for_deployment(client, config, version):
            test_deployment(client, config)
            print("\n✅ Deployment complete!")
            print(f"   Agent name: {config['agent_name']}")
            print(f"   Version: {version}")
            print(f"   Project: {config['project_endpoint']}")
        else:
            print("\n❌ Deployment did not complete within timeout.")
            sys.exit(3)

    finally:
        # Clean up temporary ZIP
        if zip_path.exists():
            zip_path.unlink()
            print(f"\n🧹 Cleaned up temporary package")


if __name__ == "__main__":
    main()
