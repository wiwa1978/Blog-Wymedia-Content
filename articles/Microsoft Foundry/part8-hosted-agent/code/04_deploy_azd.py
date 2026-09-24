#!/usr/bin/env python3
"""
Deploy the hosted agent with Azure Developer CLI.

This script writes the azd metadata files for the current agent, configures an
azd environment from .env, runs azd deploy, and sends a local smoke-test request
through the azd-hosted local runner when requested.

Usage:
    python 04_deploy_azd.py

Required .env values:
    AZURE_AI_PROJECT_ENDPOINT - Foundry project endpoint URL
    MODEL_DEPLOYMENT - Model deployment name

Optional .env values:
    AZD_AGENT_NAME - Hosted agent name
    AZD_ENV_NAME - azd environment name
    AZD_PROJECT_ID - Full ARM ID of the existing Foundry project
    TEST_PROMPT - Smoke-test prompt
    AZD_SKIP_INIT - Set true to skip azd ai agent init
    AZD_RUN_LOCAL_TEST - Set true to run azd ai agent run/invoke locally

Exit codes:
    0 - Deployment successful
    1 - Configuration error
    2 - azd command failed
"""
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

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

    return {
        "project_endpoint": require_env("AZURE_AI_PROJECT_ENDPOINT"),
        "model_deployment": require_env("MODEL_DEPLOYMENT"),
        "agent_name": os.getenv("AZD_AGENT_NAME", "mcp-knowledge-agent-azd"),
        "env_name": os.getenv("AZD_ENV_NAME", "mcp-knowledge-agent-dev"),
        "project_id": os.getenv("AZD_PROJECT_ID"),
        "test_prompt": os.getenv("TEST_PROMPT", DEFAULT_TEST_PROMPT),
        "skip_init": os.getenv("AZD_SKIP_INIT", "false").lower() == "true",
        "run_local_test": os.getenv("AZD_RUN_LOCAL_TEST", "false").lower() == "true",
    }


def write_azd_files(code_dir: Path, config: dict) -> None:
    azure_yaml = code_dir / "azure.yaml"
    azure_yaml.write_text(
        textwrap.dedent(
            f"""\
            # yaml-language-server: $schema=https://raw.githubusercontent.com/Azure/azure-dev/main/schemas/v1.0/azure.yaml.json

            name: {config["agent_name"]}
            services:
              {config["agent_name"]}:
                project: .
                host: azure.ai.agent
                env:
                  AZURE_AI_PROJECT_ENDPOINT: ${{AZURE_AI_PROJECT_ENDPOINT}}
                  MODEL_DEPLOYMENT: ${{MODEL_DEPLOYMENT}}
                codeConfiguration:
                  dependencyResolution: remote_build
                  entryPoint: 00_create_agent.py
                  runtime: python_3_13
                kind: hosted
                name: {config["agent_name"]}
              foundry-project:
                host: azure.ai.project
                endpoint: ${{AZURE_AI_PROJECT_ENDPOINT}}
            """
        ),
        encoding="utf-8",
    )
    print("Wrote azure.yaml")

    agentignore = code_dir / ".agentignore"
    agentignore.write_text(
        "\n".join(
            [
                "# Files excluded from agent code deployment packaging.",
                ".env",
                ".env.*",
                ".azure/",
                ".git/",
                "__pycache__/",
                ".venv/",
                "venv/",
                "*.pyc",
                ".dockerignore",
                "Dockerfile",
                "03_deploy_container.py",
                "04_deploy_azd.py",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print("Wrote .agentignore")


def run_command(args: list[str], cwd: Path, allow_failure: bool = False) -> None:
    print(f"> {' '.join(args)}")
    try:
        subprocess.run(args, cwd=cwd, check=True)
    except FileNotFoundError:
        print(f"Error: command not found: {args[0]}")
        sys.exit(2)
    except subprocess.CalledProcessError as exc:
        if allow_failure:
            print(f"Command failed with exit code {exc.returncode}; continuing.")
            return
        print(f"Error: command failed with exit code {exc.returncode}")
        sys.exit(2)


def configure_azd_environment(code_dir: Path, config: dict) -> None:
    run_command(["azd", "env", "select", config["env_name"]], code_dir, allow_failure=True)
    run_command(["azd", "env", "new", config["env_name"]], code_dir, allow_failure=True)
    run_command(["azd", "env", "select", config["env_name"]], code_dir)
    run_command(
        ["azd", "env", "set", "AZURE_AI_PROJECT_ENDPOINT", config["project_endpoint"]],
        code_dir,
    )
    run_command(["azd", "env", "set", "MODEL_DEPLOYMENT", config["model_deployment"]], code_dir)


def initialize_azd_agent(code_dir: Path, config: dict) -> None:
    if config["skip_init"]:
        print("Skipping azd ai agent init because AZD_SKIP_INIT=true")
        return

    if not config["project_id"]:
        print(
            "AZD_PROJECT_ID is not set; skipping azd ai agent init. "
            "Set AZD_PROJECT_ID to the full Foundry project ARM ID if this "
            "folder has not been initialized before."
        )
        return

    run_command(
        [
            "azd",
            "ai",
            "agent",
            "init",
            "--no-prompt",
            "--project-id",
            config["project_id"],
            "--deploy-mode",
            "code",
            "--runtime",
            "python_3_13",
            "--entry-point",
            "00_create_agent.py",
            "--dep-resolution",
            "remote_build",
            "--src",
            ".",
        ],
        code_dir,
        allow_failure=True,
    )


def deploy_with_azd(code_dir: Path) -> None:
    run_command(["azd", "deploy"], code_dir)


def run_local_smoke_test(code_dir: Path, config: dict) -> None:
    if not config["run_local_test"]:
        print("Skipping local azd smoke test. Set AZD_RUN_LOCAL_TEST=true to enable it.")
        return

    process = subprocess.Popen(["azd", "ai", "agent", "run"], cwd=code_dir)
    try:
        time.sleep(8)
        run_command(["azd", "ai", "agent", "invoke", "--local", config["test_prompt"]], code_dir)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def main() -> None:
    code_dir = Path(__file__).parent.resolve()
    print("=" * 72)
    print("Deploy Hosted Agent via Azure Developer CLI")
    print("=" * 72)

    config = load_config(code_dir)
    write_azd_files(code_dir, config)
    configure_azd_environment(code_dir, config)
    initialize_azd_agent(code_dir, config)
    deploy_with_azd(code_dir)
    run_local_smoke_test(code_dir, config)

    print("\nDeployment complete.")
    print(f"Agent name: {config['agent_name']}")
    print(f"azd environment: {config['env_name']}")
    print(f"Project: {config['project_endpoint']}")


if __name__ == "__main__":
    main()
