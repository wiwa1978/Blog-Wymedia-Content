"""Generate an MP3 speech file with an audio-enabled Microsoft Foundry model."""

import base64
import os
from datetime import datetime
from pathlib import Path

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import APIStatusError, OpenAI


load_dotenv()

PROJECT_ENDPOINT = os.environ["PROJECT_ENDPOINT"].rstrip("/")
MODEL = os.environ["MODEL"]
VOICE = os.getenv("VOICE", "alloy")
TEXT = os.getenv("TEXT", "").strip()
TEXT_FILE = os.getenv("TEXT_FILE", "prompt.txt").strip()
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "speech")


def project_openai_base_url(project_endpoint: str) -> str:
    """Derive the project-scoped OpenAI endpoint from a Foundry project URL."""
    marker = ".services.ai.azure.com"
    if marker not in project_endpoint:
        raise ValueError(
            "PROJECT_ENDPOINT must look like "
            "https://<resource>.services.ai.azure.com/api/projects/<project>."
        )
    resource_host = project_endpoint.split("://", 1)[1].split("/", 1)[0]
    return f"https://{resource_host}/openai/v1"


def input_text() -> str:
    if TEXT:
        return TEXT

    prompt_path = Path(TEXT_FILE)
    if prompt_path.exists():
        text = prompt_path.read_text(encoding="utf-8").strip()
        if text:
            return text

    raise ValueError(
        f"Set TEXT in .env, or create '{TEXT_FILE}' with the text to read aloud."
    )


credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(
    credential,
    "https://ai.azure.com/.default",
)
client = OpenAI(
    base_url=project_openai_base_url(PROJECT_ENDPOINT),
    api_key=token_provider,
)

text = input_text()
try:
    response = client.chat.completions.create(
        model=MODEL,
        modalities=["text", "audio"],
        audio={"voice": VOICE, "format": "mp3"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a text-to-speech engine. Read the user's text aloud "
                    "verbatim. Do not answer it, paraphrase it, or add any words."
                ),
            },
            {"role": "user", "content": text},
        ],
    )
except APIStatusError as exc:
    if exc.status_code == 404 or "DeploymentNotFound" in str(exc):
        raise RuntimeError(
            f"Deployment '{MODEL}' was not found or does not support audio "
            "completions. Set MODEL to the exact audio deployment name in "
            "Microsoft Foundry."
        ) from exc
    raise

audio = response.choices[0].message.audio
if not audio or not audio.data:
    raise RuntimeError("The model response did not contain audio data.")

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
safe_model = "".join(
    character if character.isalnum() or character in "-_" else "_"
    for character in MODEL
)
output_path = Path(f"{OUTPUT_FILE}_{safe_model}_{timestamp}.mp3")
output_path.write_bytes(base64.b64decode(audio.data))
print(f"Saved audio to {output_path}")
