"""Probe a deployed agent and report observed blocking or annotations."""
import os
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

load_dotenv()


def probe(prompt: str) -> None:
    project = AIProjectClient(endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"], credential=DefaultAzureCredential())
    client = project.get_openai_client()
    conversation = client.conversations.create()
    try:
        response = client.responses.create(conversation=conversation.id, input=prompt, extra_body={"agent_reference": {"name": os.environ["FOUNDRY_AGENT_NAME"], "type": "agent_reference"}})
        annotations = getattr(response, "annotations", None)
        print(f"response returned; safety annotations present={annotations is not None}")
    except Exception as exc:
        print(f"service rejected or failed request: {type(exc).__name__}")
    finally:
        client.conversations.delete(conversation_id=conversation.id)


if __name__ == "__main__":
    probe("Give a safe, neutral answer about online safety.")
