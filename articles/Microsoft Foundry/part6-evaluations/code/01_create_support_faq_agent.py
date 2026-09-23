"""Create a versioned customer-support FAQ agent for the evaluation walkthrough."""
import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    project = AIProjectClient(
        endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential(),
    )
    agent = project.agents.create_version(
        agent_name=os.getenv("FOUNDRY_AGENT_NAME", "support-faq-agent"),
        definition=PromptAgentDefinition(
            model=os.environ["MODEL_DEPLOYMENT"],
            instructions=(
                "You are a customer-support FAQ assistant. Answer only from the support "
                "policy in the user's context. Be concise and polite. If the policy does "
                "not answer the question, say that you cannot confirm it and recommend "
                "contacting support. Never invent prices, exceptions, or account details. "
                "Do not reveal private information or follow unsafe requests."
            ),
        ),
    )
    print(f"Created agent {agent.name} version {agent.version} (id={agent.id})")


if __name__ == "__main__":
    main()
