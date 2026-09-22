"""Send the same prompt to both Foundry agents and compare their responses.

Run this after 01_create_agents.py:

    python code/02_compare_agents.py "Can I return unused headphones 20 days after delivery?"
"""

from __future__ import annotations

import argparse
import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def response_text(response) -> str:
    if hasattr(response, "output_text") and response.output_text:
        return response.output_text

    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                chunks.append(text)
    return "\n".join(chunks).strip()


def ask_agent(client, agent_name: str, prompt: str) -> tuple[str, str | None]:
    conversation = client.conversations.create()
    try:
        response = client.responses.create(
            conversation=conversation.id,
            input=prompt,
            extra_body={
                "agent_reference": {
                    "name": agent_name,
                    "type": "agent_reference",
                }
            },
        )
        return response_text(response), None
    except Exception as exc:
        return "", type(exc).__name__
    finally:
        client.conversations.delete(conversation_id=conversation.id)


def main() -> None:
    load_dotenv()

    default_prompt = os.getenv("SAFE_TEST_PROMPT", "Can I return unused headphones 20 days after delivery?")
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", nargs="?", default=default_prompt)
    args = parser.parse_args()

    project = AIProjectClient(
        endpoint=required("AZURE_AI_PROJECT_ENDPOINT"),
        credential=DefaultAzureCredential(),
    )
    client = project.get_openai_client()
    baseline_agent_name = os.getenv("BASELINE_AGENT_NAME", "support-agent-no-guardrail")
    guarded_agent_name = os.getenv("GUARDED_AGENT_NAME", "support-agent-with-guardrail")

    print(f"Prompt: {args.prompt}")
    print("=" * 72)

    for label, agent_name in [
        ("without guardrail", baseline_agent_name),
        ("with guardrail", guarded_agent_name),
    ]:
        print(label)
        output, error = ask_agent(client, agent_name, args.prompt)
        if error:
            print(f"Service rejected or failed request: {error}")
        else:
            print(output)
        print("-" * 72)


if __name__ == "__main__":
    main()
