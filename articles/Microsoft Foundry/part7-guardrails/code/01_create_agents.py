"""Create two Foundry agents: one without and one with an RAI guardrail.

Run this first:

    python code/01_create_agents.py

Then open both agents in the Foundry playground and compare their behavior.
"""

from __future__ import annotations

import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, RaiConfig
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


SUPPORT_POLICY = """
Contoso Audio return policy:
- Standard returns are accepted within 30 days of delivery when the item is unused.
- Damaged or defective items must be reported within 14 days of delivery.
- Support can provide a prepaid return label after basic verification.
- Refunds are issued only after the returned item is received and inspected.
- Agents must not reveal private account, address, payment, or order details.
- Agents must not issue refunds, cancel orders, or change account data directly.
- Questions outside the policy should be answered with a limitation and a support handoff.
""".strip()


AGENT_INSTRUCTIONS = f"""
You are a customer-support FAQ assistant for Contoso Audio.

Answer from the policy below. Be concise and helpful.

Support policy:
{SUPPORT_POLICY}
""".strip()


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    load_dotenv(Path(__file__).resolve().with_name(".env"))

    project = AIProjectClient(
        endpoint=required("AZURE_AI_PROJECT_ENDPOINT"),
        credential=DefaultAzureCredential(),
        allow_preview=True,
    )
    model = required("MODEL_DEPLOYMENT")
    baseline_agent_name = os.getenv("BASELINE_AGENT_NAME", "support-agent-no-guardrail")
    guarded_agent_name = os.getenv("GUARDED_AGENT_NAME", "support-agent-with-custom-guardrail")
    rai_policy_name = required("FOUNDRY_RAI_POLICY_NAME")

    baseline_agent = project.agents.create_version(
        agent_name=baseline_agent_name,
        definition=PromptAgentDefinition(
            model=model,
            instructions=AGENT_INSTRUCTIONS,
        ),
    )
    guarded_definition = PromptAgentDefinition(
        model=model,
        instructions=AGENT_INSTRUCTIONS,
        rai_config=RaiConfig(rai_policy_name=rai_policy_name),
    )
    configured_policy = guarded_definition.rai_config.rai_policy_name
    if configured_policy != rai_policy_name:
        raise RuntimeError(
            f"RAI policy was not retained by the SDK: expected {rai_policy_name!r}, "
            f"got {configured_policy!r}"
        )

    guarded_agent = project.agents.create_version(
        agent_name=guarded_agent_name,
        definition=guarded_definition,
    )

    print("Created comparison agents:")
    print(f"- without guardrail: {baseline_agent_name} version {getattr(baseline_agent, 'version', 'unknown')}")
    print(f"- with guardrail:    {guarded_agent_name} version {getattr(guarded_agent, 'version', 'unknown')}")
    print(f"Guarded agent RAI policy: {rai_policy_name}")
    print("The guarded definition contains the custom RAI policy.")
    print("\nNext: open both agents in the Foundry playground and send the same prompts.")


if __name__ == "__main__":
    main()
