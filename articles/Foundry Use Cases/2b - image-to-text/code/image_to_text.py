import base64
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlsplit

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import OpenAI


SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")


def required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or ("<" in value and ">" in value):
        raise ValueError(f"Set {name} in .env before running this script.")
    return value


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else SCRIPT_DIR / path


PROJECT_ENDPOINT = required_setting("PROJECT_ENDPOINT")
MODEL = required_setting("MODEL")
INPUT_FILE = resolve_path(required_setting("INPUT_FILE"))
PROMPT = required_setting("PROMPT")
DETAIL = os.getenv("DETAIL", "auto").strip().lower()
OUTPUT_FILE = resolve_path(os.getenv("OUTPUT_FILE", "output.txt"))

if not INPUT_FILE.is_file():
    raise FileNotFoundError(f"Input image was not found: {INPUT_FILE}")

if DETAIL not in {"auto", "low", "high"}:
    raise ValueError("DETAIL must be one of: auto, low, high.")

mime_type, _ = mimetypes.guess_type(INPUT_FILE.name)
supported_image_types = {"image/png", "image/jpeg", "image/webp"}
if mime_type not in supported_image_types:
    raise ValueError("INPUT_FILE must be a PNG, JPEG, or WebP image.")

project_url = urlsplit(PROJECT_ENDPOINT.rstrip("/"))
if project_url.scheme != "https" or not project_url.netloc:
    raise ValueError("PROJECT_ENDPOINT must be an absolute HTTPS Foundry project endpoint.")

image_bytes = INPUT_FILE.read_bytes()
if len(image_bytes) >= 50 * 1024 * 1024:
    raise ValueError("The input image must be smaller than 50 MB.")
encoded_image = base64.b64encode(image_bytes).decode("ascii")
image_data_url = f"data:{mime_type};base64,{encoded_image}"
openai_base_url = f"{PROJECT_ENDPOINT.rstrip('/')}/openai/v1"

with DefaultAzureCredential() as credential:
    token_provider = get_bearer_token_provider(
        credential,
        "https://ai.azure.com/.default",
    )
    with OpenAI(base_url=openai_base_url, api_key=token_provider) as client:
        response = client.responses.create(
            model=MODEL,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": PROMPT},
                        {
                            "type": "input_image",
                            "image_url": image_data_url,
                            "detail": DETAIL,
                        },
                    ],
                }
            ],
        )

answer = response.output_text.strip()
if not answer:
    raise RuntimeError("The model returned no text.")

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE.write_text(answer + "\n", encoding="utf-8")
print(answer)
print(f"\nSaved response to {OUTPUT_FILE}")
