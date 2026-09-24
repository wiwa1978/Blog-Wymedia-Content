---
title: "Image To Image"
excerpt: "Image-to-image lets you take an existing picture and transform it with a text instruction — restyle a photo, swap a background, or turn a sketch into a polished illustration. With Microsoft Foundry this is a single call to the image editing endpoint: send your source image plus a prompt, get back an edited image."
slug: foundry-use-cases/image-to-image
articleId: e4ad8d43-d6a3-4075-83ba-90ca9087715f
artifactPath: "Foundry Use Cases/image-to-image"
tags: ["Microsoft Foundry", "Azure AI", "Python", "image generation"]
series: {"slug":"foundry-use-cases","title":"Microsoft Foundry - Use Cases","part":3}
publishAt: "2026-09-26T15:25:00.000Z"
---
# Getting Started: Image to Image with Microsoft Foundry

Image-to-image lets you take an existing picture and transform it with a text instruction — restyle a photo, swap a background, or turn a sketch into a polished illustration. With Microsoft Foundry this is a single call to the image editing endpoint: send your source image plus a prompt, get back an edited image.

## What you need

1. A **Foundry project** with an image-editing-capable model deployment (e.g. `gpt-image-1`).
2. **Azure CLI login** (`az login`) with the *Azure AI User* role on the project — or any identity `DefaultAzureCredential` can pick up. No API keys to manage.
3. Two Python packages:

```bash
pip install openai azure-identity
```

## The core idea

Editing an image against a Foundry deployment boils down to four steps:

1. **Authenticate** — get a token provider Foundry trusts.
2. **Create an OpenAI client** — point the standard `openai` SDK's `base_url` at your Foundry endpoint instead of `api.openai.com`.
3. **Call `images.edit`** — pass your source image file plus the instruction prompt.
4. **Decode and save** — the response returns the edited image as base64; decode it to bytes and write it to a file.

```python
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://ai.azure.com/.default"
)
client = OpenAI(
    base_url="https://<resource-name>.services.ai.azure.com/openai/v1",
    api_key=token_provider,
)
with open("input.png", "rb") as source_image:
    response = client.images.edit(
        model="gpt-image-1",
        image=source_image,
        prompt="Turn this into a vibrant, hand-drawn comic-book style illustration",
        size="1024x1024",
    )
```

`response.data[0].b64_json` is your edited image, base64-encoded — decode it with `base64.b64decode(...)` and write the bytes to a `.png` file.

## The full script

The attached [`image_to_image.py`](/articles/foundry-use-cases/image-to-image/code/image_to_image.py) wraps this into a runnable script: set your `ENDPOINT`, `MODEL`, and `PROMPT` at the top of the file, place a source image next to it (the script expects `input.png` by default), then run it.

```bash
python Code/image_to_image.py
```

```
Saved edited image to edited_image.png
```

## What we intentionally left out

The production Image to Image use case in this repo adds several things on top of these fundamentals: file-type and size validation for uploaded images, model-capability checks, structured error handling for editing failures, conversation persistence, and telemetry. None of that changes the core mechanic shown above — it's still one call to `images.edit` with an image and a prompt. Once you're comfortable with this minimal version, swapping in a different source image or prompt is a small step from here.

## Try it yourself

Open `Code/image_to_image.py`, set `ENDPOINT` and `MODEL` to your own Foundry project and image deployment, drop a sample image in as `input.png`, and run it — you'll have an edited PNG on disk in seconds.
