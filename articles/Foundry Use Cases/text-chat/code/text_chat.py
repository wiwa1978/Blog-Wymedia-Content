import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai import NotFoundError

SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")


def required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("<"):
        raise ValueError(f"Set {name} in .env before running this script.")
    return value


PROJECT_ENDPOINT = required_setting("PROJECT_ENDPOINT")
MODEL = required_setting("MODEL")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "").strip()
PROMPT = os.getenv("PROMPT", "").strip()


def stream_chat(openai_client, messages: list[dict[str, str]]) -> str:
    try:
        stream = openai_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            stream=True,
        )
        answer: list[str] = []
        for event in stream:
            if event.choices and event.choices[0].delta.content:
                content = event.choices[0].delta.content
                answer.append(content)
                print(content, end="", flush=True)
        print()
        return "".join(answer)
    except NotFoundError as exc:
        raise RuntimeError(
            f"Foundry deployment '{MODEL}' was not found. Set MODEL to the exact "
            "deployment name shown in the project's Deployed models page."
        ) from exc


def messages_for(history: list[dict[str, str]], prompt: str) -> list[dict[str, str]]:
    messages = list(history)
    messages.append({"role": "user", "content": prompt})
    return messages


with (
    DefaultAzureCredential() as credential,
    AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential) as project_client,
    project_client.get_openai_client() as openai_client,
):
    history: list[dict[str, str]] = []
    if SYSTEM_PROMPT:
        history.append({"role": "system", "content": SYSTEM_PROMPT})

    if PROMPT:
        print(f"Assistant ({MODEL}): ", end="")
        stream_chat(openai_client, messages_for(history, PROMPT))
    else:
        print(f"Chatting with '{MODEL}'. Type 'exit' or 'quit' to stop.\n")
        while True:
            prompt = input("You: ").strip()
            if prompt.lower() in {"exit", "quit"}:
                break
            if not prompt:
                continue

            print("Assistant: ", end="")
            request_messages = messages_for(history, prompt)
            answer = stream_chat(openai_client, request_messages)
            history.extend(
                [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": answer},
                ]
            )
