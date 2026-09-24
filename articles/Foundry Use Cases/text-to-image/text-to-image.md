---
title: "Foundry use case: text to image"
excerpt: "Text-to-image generation turns a written description into a picture — useful for marketing assets, mockups, illustrations, or just exploring ideas without opening a design tool. With Microsoft Foundry, generating an image is a single API call against your project's OpenAI-compatible image endpoint."
slug: foundry-use-cases/text-to-image
articleId: 42d9d604-3848-42d3-9ce0-8f3309486a7f
artifactPath: "Foundry Use Cases/text-to-image"
tags: ["Microsoft Foundry", "Azure AI", "Python", "image generation"]
series: {"slug":"foundry-use-cases","title":"Microsoft Foundry - Use Cases","part":9}
publishAt: "2026-09-15T13:26:00.000Z"
---
# Getting Started: Text to Image with Microsoft Foundry

Text-to-image generation turns a written description into a picture — useful for marketing assets, mockups, illustrations, or just exploring ideas without opening a design tool. With Microsoft Foundry, generating an image is a single API call against your project's OpenAI-compatible image endpoint.

## What you need

1. A **Foundry project** with an image-capable model deployment (e.g. `gpt-image-1`).
2. **Azure CLI login** (`az login`) with the *Azure AI User* role on the project — or any identity `DefaultAzureCredential` can pick up. No API keys to manage.
3. Two Python packages:

```bash
pip install openai azure-identity
```

## The core idea

Generating an image against a Foundry deployment boils down to four steps:

1. **Authenticate** — get a token provider Foundry trusts.
2. **Create an OpenAI client** — point the standard `openai` SDK's `base_url` at your Foundry endpoint instead of `api.openai.com`.
3. **Call `images.generate`** — same shape as calling OpenAI directly, just pointed at your deployment.
4. **Decode and save** — the response returns the image as base64; decode it to bytes and write it to a file.

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
response = client.images.generate(
    model="gpt-image-1",
    prompt="A watercolor painting of a lighthouse at sunset",
    size="1024x1024",
)
```

`response.data[0].b64_json` is your image, base64-encoded — decode it with `base64.b64decode(...)` and write the bytes to a `.png` file.

## The full script

The attached [`text_to_image.py`](/articles/foundry-use-cases/text-to-image/code/text_to_image.py) wraps this into a runnable script: set your `ENDPOINT`, `MODEL`, and `PROMPT` at the top of the file, then run it.

```bash
python Code/text_to_image.py
```

```
Saved image to generated_image.png
```

## What we intentionally left out

The production Text to Image use case in this repo layers a lot on top of these fundamentals: a model picker across multiple image providers (OpenAI, FLUX, MAI), content-policy error handling with user-friendly messages, saving generated images to a shared gallery, conversation persistence, and telemetry. None of that changes the core mechanic shown above — it's still one call to `images.generate`. Once you're comfortable with this minimal version, adding a different `size`, richer prompts, or looping over several prompts is a small step from here.

## Try it yourself

Open `Code/text_to_image.py`, set `ENDPOINT` and `MODEL` to your own Foundry project and image deployment, and run it — you'll have a generated PNG on disk in seconds.
