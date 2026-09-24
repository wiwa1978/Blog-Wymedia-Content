# pip install openai azure-identity

import base64

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI

ENDPOINT = "https://<resource-name>.services.ai.azure.com/openai/v1"
MODEL = "gpt-image-1"
PROMPT = "Turn this into a vibrant, hand-drawn comic-book style illustration"
INPUT_FILE = "input.png"  # place a sample PNG/JPEG/WebP next to this script
OUTPUT_FILE = "edited_image.png"

# 1. Authenticate. `DefaultAzureCredential` picks up `az login`, a managed
#    identity, etc. The token provider refreshes tokens for us automatically.
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://ai.azure.com/.default",
)

# 2. Point the standard OpenAI SDK at your Foundry endpoint instead of openai.com.
client = OpenAI(base_url=ENDPOINT, api_key=token_provider)

# 3. Call the image edit endpoint with the source image + instruction prompt.
with open(INPUT_FILE, "rb") as source_image:
    response = client.images.edit(
        model=MODEL,
        image=source_image,
        prompt=PROMPT,
        size="1024x1024",
    )

# 4. The edited image comes back base64-encoded; decode it and save it to disk.
image_bytes = base64.b64decode(response.data[0].b64_json)
with open(OUTPUT_FILE, "wb") as f:
    f.write(image_bytes)

print(f"Saved edited image to {OUTPUT_FILE}")
