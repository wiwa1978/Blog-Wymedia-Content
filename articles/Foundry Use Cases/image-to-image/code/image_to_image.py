import base64
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import NotFoundError, OpenAI

SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")


def required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("<"):
        raise ValueError(f"Set {name} in .env before running this script.")
    return value


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else SCRIPT_DIR / path


def load_prompt() -> str:
    prompt_file = os.getenv("PROMPT_FILE", "").strip()
    if prompt_file:
        prompt = resolve_path(prompt_file).read_text(encoding="utf-8").strip()
        if not prompt:
            raise ValueError(f"{resolve_path(prompt_file)} is empty.")
        return prompt
    return required_setting("PROMPT")


def image_size(width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        raise ValueError("WIDTH and HEIGHT must be positive integers.")
    if width == height:
        return "1024x1024"
    return "1536x1024" if width > height else "1024x1536"


def output_path(base_file: str, model: str) -> Path:
    path = resolve_path(base_file)
    extension = path.suffix or ".png"
    model_slug = re.sub(r"[^A-Za-z0-9._-]+", "-", model).strip("-") or "model"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return path.with_name(f"{path.stem}_{model_slug}_{timestamp}{extension}")


PROJECT_ENDPOINT = required_setting("PROJECT_ENDPOINT")
MODEL = required_setting("MODEL")
INPUT_FILE = resolve_path(required_setting("INPUT_FILE"))
PROMPT = load_prompt()
WIDTH = int(os.getenv("WIDTH", "1024"))
HEIGHT = int(os.getenv("HEIGHT", "1024"))
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "edited_image.png")

if not INPUT_FILE.is_file():
    raise FileNotFoundError(f"Input image was not found: {INPUT_FILE}")

project_url = urlsplit(PROJECT_ENDPOINT.rstrip("/"))
if project_url.scheme != "https" or not project_url.netloc:
    raise ValueError("PROJECT_ENDPOINT must be an absolute HTTPS Foundry project endpoint.")

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://ai.azure.com/.default",
)
openai_base_url = f"{project_url.scheme}://{project_url.netloc}/openai/v1"

with (
    OpenAI(base_url=openai_base_url, api_key=token_provider) as openai_client,
    INPUT_FILE.open("rb") as source_image,
):
    try:
        response = openai_client.images.edit(
            model=MODEL,
            image=source_image,
            prompt=PROMPT,
            size=image_size(WIDTH, HEIGHT),
        )
    except NotFoundError as exc:
        raise RuntimeError(
            f"Image edit deployment or route was not found for '{MODEL}'. "
            "Verify that the deployment supports image edits and that PROJECT_ENDPOINT "
            "is the Foundry project endpoint."
        ) from exc

image_data = response.data[0].b64_json
if not image_data:
    raise RuntimeError("Image edit returned no base64 image data.")

output_file = output_path(OUTPUT_FILE, MODEL)
output_file.write_bytes(base64.b64decode(image_data))
print(f"Saved edited image to {output_file}")
