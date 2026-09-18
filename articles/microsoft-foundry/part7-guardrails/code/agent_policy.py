"""Bind a Foundry RAI policy to an agent version."""
import os
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, RaiConfig
from azure.identity import DefaultAzureCredential

load_dotenv()


def main() -> None:
    project = AIProjectClient(endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"], credential=DefaultAzureCredential())
    agent_name = os.getenv("FOUNDRY_AGENT_NAME", "policy-demo")
    policy_id = os.environ["FOUNDRY_RAI_POLICY_ID"]
    definition = PromptAgentDefinition(
        model=os.environ["MODEL_DEPLOYMENT"],
        instructions=(
            "Refuse requests for private data. Ask for confirmation before consequential "
            "actions. Use only explicitly approved tools and report uncertainty."
        ),
        rai_config=RaiConfig(rai_policy_name=policy_id),
    )
    agent = project.agents.create_version(agent_name=agent_name, definition=definition)
    print(f"Created agent {agent.name} version {agent.version} with RAI policy {policy_id}")


if __name__ == "__main__":
    main()
