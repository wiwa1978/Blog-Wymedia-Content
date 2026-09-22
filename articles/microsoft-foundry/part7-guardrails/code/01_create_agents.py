"""Create two Foundry agents: one without and one with an RAI guardrail.

Run this first:

    python code/01_create_agents.py

Then open both agents in the Foundry playground and compare their behavior.
"""

from __future__ import annotations

import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import HostedAgentDefinition, RaiConfig
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


BASELINE_INSTRUCTIONS = f"""
You are a customer-support FAQ assistant for Contoso Audio.

Answer from the policy below. Be concise and helpful.

Support policy:
{SUPPORT_POLICY}
""".strip()


GUARDED_INSTRUCTIONS = f"""
You are a customer-support FAQ assistant for Contoso Audio.

Use only the policy below and the user's current question. Be concise and polite.
If the policy does not answer the question, say you cannot confirm it and suggest
contacting support. Do not invent exceptions, prices, order states, addresses,
payment details, or internal process details.

Never perform consequential actions such as issuing a refund, changing an order,
canceling a subscription, or disclosing private customer data. If the user asks
for such an action, explain the limitation and direct them to the approved support
channel.

Support policy:
{SUPPORT_POLICY}
""".strip()


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    load_dotenv()

    project = AIProjectClient(
        endpoint=required("AZURE_AI_PROJECT_ENDPOINT"),
        credential=DefaultAzureCredential(),
    )
    model = required("MODEL_DEPLOYMENT")
    baseline_agent_name = os.getenv("BASELINE_AGENT_NAME", "support-agent-no-guardrail")
    guarded_agent_name = os.getenv("GUARDED_AGENT_NAME", "support-agent-with-guardrail")
    rai_policy_name = os.getenv("FOUNDRY_RAI_POLICY_NAME") or "Microsoft.DefaultV2"

    baseline_agent = project.agents.create_version(
        agent_name=baseline_agent_name,
        definition=HostedAgentDefinition(
            model=model,
            instructions=BASELINE_INSTRUCTIONS,
        ),
    )
    guarded_agent = project.agents.create_version(
        agent_name=guarded_agent_name,
        definition=HostedAgentDefinition(
            model=model,
            instructions=GUARDED_INSTRUCTIONS,
            rai_config=RaiConfig(rai_policy_name=rai_policy_name),
        ),
    )

    print("Created comparison agents:")
    print(f"- without guardrail: {baseline_agent_name} version {getattr(baseline_agent, 'version', 'unknown')}")
    print(f"- with guardrail:    {guarded_agent_name} version {getattr(guarded_agent, 'version', 'unknown')}")
    print(f"Guarded agent RAI policy: {rai_policy_name}")
    print("\nNext: open both agents in the Foundry playground and send the same prompts.")


if __name__ == "__main__":
    main()
