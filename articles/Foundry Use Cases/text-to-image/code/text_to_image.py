# pip install -r requirements.txt
import base64
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
import requests

SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")


def required_setting(name):
    value = os.getenv(name)
    if not value or value.startswith("<"):
        raise ValueError(f"Set {name} in .env before running this script.")
    return value


def load_prompt():
    prompt_file = os.getenv("PROMPT_FILE")
    if prompt_file:
        path = Path(prompt_file)
        if not path.is_absolute():
            path = SCRIPT_DIR / path
        prompt = path.read_text(encoding="utf-8").strip()
        if not prompt:
            raise ValueError(f"{path} is empty.")
        return prompt
    return required_setting("PROMPT")


def output_path(base_file, model):
    path = Path(base_file)
    extension = path.suffix or ".png"
    model_slug = re.sub(r"[^A-Za-z0-9._-]+", "-", model).strip("-") or "model"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return path.with_name(f"{path.stem}_{model_slug}_{timestamp}{extension}")


PROJECT_ENDPOINT = required_setting("PROJECT_ENDPOINT")
project_url = urlsplit(PROJECT_ENDPOINT)
MODEL = required_setting("MODEL")
PROMPT = load_prompt()
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "generated_image.png")
WIDTH = int(os.getenv("WIDTH", "1024"))
HEIGHT = int(os.getenv("HEIGHT", "1024"))

foundry_origin = f"{project_url.scheme}://{project_url.netloc}"
normalized_model = MODEL.strip().lower()

if "mai-image" in normalized_model:
    url = f"{foundry_origin}/mai/v1/images/generations"
    token_scope = "https://cognitiveservices.azure.com/.default"
    payload = {
        "model": MODEL,
        "prompt": PROMPT,
        "width": WIDTH,
        "height": HEIGHT,
    }
else:
    url = f"{foundry_origin}/openai/v1/images/generations"
    token_scope = "https://ai.azure.com/.default"
    payload = {
        "model": MODEL,
        "prompt": PROMPT,
        "size": f"{WIDTH}x{HEIGHT}",
    }

# 1. Authenticate. `DefaultAzureCredential` picks up `az login`, a managed
#    identity, etc. The token provider refreshes tokens for us automatically.
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    token_scope,
)

# 2. Call the image endpoint for the configured deployment family.
response = requests.post(
    url,
    headers={
        "Authorization": f"Bearer {token_provider()}",
        "Content-Type": "application/json",
    },
    json=payload,
    timeout=180,
)
if not response.ok:
    raise RuntimeError(f"Image generation failed ({response.status_code}): {response.text}")

result = response.json()
images = result.get("data") or [result]
if isinstance(images, dict):
    images = [images]

image = images[0]
encoded_image = image.get("b64_json") or image.get("base64") or image.get("image")
image_url = image.get("url")
if encoded_image:
    image_bytes = base64.b64decode(encoded_image)
elif image_url:
    image_response = requests.get(image_url, timeout=180)
    image_response.raise_for_status()
    image_bytes = image_response.content
else:
    raise RuntimeError("Image generation returned no image data.")

# 3. Save the generated image to disk.
output_file = output_path(OUTPUT_FILE, MODEL)
with open(output_file, "wb") as f:
    f.write(image_bytes)

print(f"Saved image to {output_file}")
