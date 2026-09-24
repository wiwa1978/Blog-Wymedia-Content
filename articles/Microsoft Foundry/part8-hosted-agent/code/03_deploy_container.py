#!/usr/bin/env python3
"""
Deploy the hosted agent as a container image.

This script builds a Docker image from the local agent source, pushes it to
Azure Container Registry, registers the image as a Foundry hosted-agent version,
waits until that version is active, and sends a smoke-test request.

Usage:
    python 03_deploy_container.py

Required .env values:
    AZURE_AI_PROJECT_ENDPOINT - Foundry project endpoint URL
    MODEL_DEPLOYMENT - Model deployment name
    ACR_NAME - Azure Container Registry name, without .azurecr.io

Optional .env values:
    CONTAINER_AGENT_NAME - Hosted agent name
    CONTAINER_IMAGE_NAME - Repository/image name in ACR
    CONTAINER_IMAGE_TAG - Image tag
    CONTAINER_CPU - CPU allocation for the hosted version
    CONTAINER_MEMORY - Memory allocation for the hosted version
    CONTAINER_REGISTRY_CONNECTION_ID - Foundry connection ID for private registry access
    TEST_PROMPT - Smoke-test prompt sent after deployment

Exit codes:
    0 - Deployment successful
    1 - Configuration error
    2 - Docker or Azure CLI command failed
    3 - Hosted-agent deployment timed out
"""
import os
import subprocess
import sys
import time
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    ContainerConfiguration,
    HostedAgentDefinition,
    ProtocolVersionRecord,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


DEFAULT_TEST_PROMPT = (
    "Read data/quantum-computing-rag-test.md and summarize how quantum "
    "computing differs from classical computing."
)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"Error: {name} is not set in .env")
        sys.exit(1)
    return value


def load_config(code_dir: Path) -> dict:
    load_dotenv(code_dir / ".env", override=True)

    acr_name = require_env("ACR_NAME")
    image_name = os.getenv("CONTAINER_IMAGE_NAME", "mcp-knowledge-agent")
    image_tag = os.getenv("CONTAINER_IMAGE_TAG", "latest")

    return {
        "project_endpoint": require_env("AZURE_AI_PROJECT_ENDPOINT"),
        "model_deployment": require_env("MODEL_DEPLOYMENT"),
        "agent_name": os.getenv("CONTAINER_AGENT_NAME", "mcp-knowledge-agent-container"),
        "acr_name": acr_name,
        "image": f"{acr_name}.azurecr.io/{image_name}:{image_tag}",
        "cpu": os.getenv("CONTAINER_CPU", "1"),
        "memory": os.getenv("CONTAINER_MEMORY", "2Gi"),
        "registry_connection_id": os.getenv("CONTAINER_REGISTRY_CONNECTION_ID"),
        "test_prompt": os.getenv("TEST_PROMPT", DEFAULT_TEST_PROMPT),
        "timeout_seconds": int(os.getenv("CONTAINER_DEPLOY_TIMEOUT_SECONDS", "600")),
    }


def ensure_container_files(code_dir: Path) -> None:
    dockerfile = code_dir / "Dockerfile"
    if not dockerfile.exists():
        dockerfile.write_text(
            "\n".join(
                [
                    "FROM python:3.13-slim",
                    "WORKDIR /app",
                    "COPY requirements.txt .",
                    "RUN pip install --no-cache-dir -r requirements.txt",
                    "COPY 00_create_agent.py tools.py ./",
                    "COPY data ./data",
                    'CMD ["python", "00_create_agent.py"]',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print("Created Dockerfile")

    dockerignore = code_dir / ".dockerignore"
    if not dockerignore.exists():
        dockerignore.write_text(
            "\n".join(
                [
                    ".env",
                    ".venv",
                    "__pycache__",
                    "*.pyc",
                    ".azure",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        print("Created .dockerignore")


def run_command(args: list[str], cwd: Path) -> None:
    print(f"> {' '.join(args)}")
    try:
        subprocess.run(args, cwd=cwd, check=True)
    except FileNotFoundError:
        print(f"Error: command not found: {args[0]}")
        sys.exit(2)
    except subprocess.CalledProcessError as exc:
        print(f"Error: command failed with exit code {exc.returncode}")
        sys.exit(2)


def build_and_push_image(code_dir: Path, config: dict) -> None:
    print("Authenticating Docker to Azure Container Registry...")
    run_command(["az", "acr", "login", "--name", config["acr_name"]], code_dir)

    print("Building container image...")
    run_command(["docker", "build", "--tag", config["image"], "."], code_dir)

    print("Pushing container image...")
    run_command(["docker", "push", config["image"]], code_dir)


def create_hosted_agent_version(config: dict):
    project = AIProjectClient(
        endpoint=config["project_endpoint"],
        credential=DefaultAzureCredential(),
    )

    container_configuration = ContainerConfiguration(image=config["image"])
    if config["registry_connection_id"]:
        container_configuration = ContainerConfiguration(
            image=config["image"],
            registry_connection_id=config["registry_connection_id"],
        )

    created = project.agents.create_version(
        agent_name=config["agent_name"],
        definition=HostedAgentDefinition(
            cpu=config["cpu"],
            memory=config["memory"],
            container_configuration=container_configuration,
            protocol_versions=[
                ProtocolVersionRecord(protocol="responses", version="2.0.0")
            ],
            environment_variables={
                "AZURE_AI_PROJECT_ENDPOINT": config["project_endpoint"],
                "MODEL_DEPLOYMENT": config["model_deployment"],
            },
        ),
        description="Markdown knowledge agent deployed from a container image.",
    )

    print(f"Created hosted-agent version: {created.version}")
    return project, created.version


def wait_until_active(project: AIProjectClient, config: dict, version: str) -> None:
    print("Waiting for hosted-agent version to become active...")
    deadline = time.time() + config["timeout_seconds"]
    attempt = 0

    while time.time() < deadline:
        attempt += 1
        time.sleep(10)
        current = project.agents.get_version(
            agent_name=config["agent_name"],
            agent_version=version,
        )
        status = current["status"]
        print(f"  Status: {status} (attempt {attempt})")

        if status == "active":
            print(f"Agent is active: {config['agent_name']} version {version}")
            return
        if status == "failed":
            raise RuntimeError(f"Hosted-agent provisioning failed: {current.get('error')}")

    print("Error: timed out waiting for hosted-agent version to become active")
    sys.exit(3)


def smoke_test(project: AIProjectClient, config: dict) -> None:
    print("Sending smoke-test request...")
    openai_client = project.get_openai_client(agent_name=config["agent_name"])
    response = openai_client.responses.create(input=config["test_prompt"])
    print("Smoke-test response:")
    print(response.output_text)


def main() -> None:
    code_dir = Path(__file__).parent.resolve()
    print("=" * 72)
    print("Deploy Hosted Agent via Container Image")
    print("=" * 72)

    config = load_config(code_dir)
    ensure_container_files(code_dir)
    build_and_push_image(code_dir, config)
    project, version = create_hosted_agent_version(config)
    wait_until_active(project, config, version)
    smoke_test(project, config)

    print("\nDeployment complete.")
    print(f"Agent name: {config['agent_name']}")
    print(f"Image: {config['image']}")
    print(f"Project: {config['project_endpoint']}")


if __name__ == "__main__":
    main()
