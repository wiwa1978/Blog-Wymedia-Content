---
title: "Text to Image"
excerpt: "Text-to-image generation turns a written description into a picture — useful for marketing assets, mockups, illustrations, or just exploring ideas without opening a design tool. With Microsoft Foundry, generating an image is a single API call against your project's OpenAI-compatible image endpoint."
slug: foundry-use-cases/text-to-image
articleId: 42d9d604-3848-42d3-9ce0-8f3309486a7f
artifactPath: "Foundry Use Cases/text-to-image"
tags: ["Microsoft Foundry", "Azure AI", "Python", "image generation"]
series: {"slug":"foundry-use-cases","title":"Microsoft Foundry - Use Cases","part":2}
publishAt: "2026-09-25T13:26:00.000Z"
---
# Getting Started: Text to Image with Microsoft Foundry

Text-to-image generation turns a written description into a picture — useful for marketing assets, mockups, illustrations, or just exploring ideas without opening a design tool. With Microsoft Foundry, generating an image is a single API call against your project's OpenAI-compatible image endpoint.

## What you need

1. A **Foundry project** with an image-capable model deployment (e.g. `MAI-Image-2.6` or `gpt-image-1`).
2. **Azure CLI login** (`az login`) with the *Azure AI User* role on the project — or any identity `DefaultAzureCredential` can pick up. No API keys to manage.
3. The Python packages listed in [`code/requirements.txt`](code/requirements.txt):

```bash
pip install -r Code/requirements.txt
```

## The core idea

Generating an image against a Foundry deployment boils down to four steps:

1. **Authenticate** — get a token provider Foundry trusts.
2. **Choose the image route** — MAI image deployments use `/mai/v1/images/generations`; Azure OpenAI image deployments use `/openai/v1/images/generations`.
3. **POST the prompt** — send the deployment name, prompt, and dimensions to the right Foundry route.
4. **Decode and save** — the response returns the image as base64, or occasionally as a temporary URL; save the bytes to a file.

```python
import os
from pathlib import Path
from urllib.parse import urlsplit

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
import requests

load_dotenv(Path(".env"))

project_url = urlsplit(os.environ["PROJECT_ENDPOINT"])
origin = f"{project_url.scheme}://{project_url.netloc}"
model = os.environ["MODEL"]
prompt_file = os.getenv("PROMPT_FILE")
prompt = Path(prompt_file).read_text(encoding="utf-8").strip() if prompt_file else os.environ["PROMPT"]
width = int(os.getenv("WIDTH", "1024"))
height = int(os.getenv("HEIGHT", "1024"))
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://cognitiveservices.azure.com/.default",
)
response = requests.post(
    f"{origin}/mai/v1/images/generations",
    headers={"Authorization": f"Bearer {token_provider()}"},
    json={"model": model, "prompt": prompt, "width": width, "height": height},
    timeout=180,
)
```

The full sample includes the matching Azure OpenAI route for `gpt-image-*` deployments and handles both base64 and URL image responses.

## The full script

The attached [`text_to_image.py`](code/text_to_image.py) wraps this into a runnable script. Copy [`code/.env.example`](code/.env.example) to `code/.env` and set your `PROJECT_ENDPOINT` and image deployment `MODEL`. Use an MAI deployment such as `MAI-Image-2.6`, or later switch the same setting to an Azure OpenAI image deployment such as `gpt-image-1`. If the model name contains `mai-image`, the script calls `/mai/v1/images/generations`; otherwise it calls `/openai/v1/images/generations`.

For short prompts, set `PROMPT` directly in `.env`. For longer multi-line prompts, especially prompts that contain quotation marks, save the text in a file such as `prompt.txt` and set `PROMPT_FILE=prompt.txt`.

`OUTPUT_FILE` is treated as the base filename. The script appends the deployment name and timestamp before the extension, for example `generated_image_MAI-Image-2.6_20260924_160530.png`.

```bash
python Code/text_to_image.py
```

```
Saved image to generated_image_MAI-Image-2.6_20260924_160530.png
```

## Microsoft Learn resources

- [Deploy and use MAI image models in Microsoft Foundry](https://learn.microsoft.com/azure/foundry/foundry-models/how-to/use-foundry-models-mai-image) — deploy MAI image models and call the `/mai/v1/images/generations` API.
- [MAI image API endpoints](https://learn.microsoft.com/azure/foundry/foundry-models/how-to/use-foundry-models-mai-image#api-endpoints) — reference the MAI image generations and edits endpoint shapes.
- [Generate images with Azure OpenAI in Azure AI Foundry Models](https://learn.microsoft.com/azure/ai-foundry/openai/dall-e-quickstart#create-a-new-python-application) — quickstart for `gpt-image-*` image generation.
- [Azure OpenAI image generation models](https://learn.microsoft.com/azure/foundry/openai/how-to/dall-e#quickstart) — REST API setup and image-generation guidance for Azure OpenAI deployments.
