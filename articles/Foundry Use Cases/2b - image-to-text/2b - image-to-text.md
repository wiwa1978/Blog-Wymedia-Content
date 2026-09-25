---
title: "Image to text"
excerpt: "Analyze a local image and turn its visual content into a text description or answer using a vision-capable Microsoft Foundry model."
slug: foundry-use-cases/image-to-text
articleId: 8826e34e-e10b-4b5e-b29f-1c9761a09531
artifactPath: "Foundry Use Cases/2b - image-to-text"
tags: ["Microsoft Foundry", "Azure AI", "Python", "image understanding"]
series: {"slug":"foundry-use-cases","title":"Microsoft Foundry - Use Cases","part":3}
publishAt: "2026-09-27T17:50:00.000Z"
---
# Getting Started: Image to Text with Microsoft Foundry

Image-to-text sends an image to a vision-capable model and asks it to describe or interpret what it sees. This is useful for generating captions, answering questions about a photo, summarizing a chart, or extracting visible text from an image.

This is the understanding counterpart to [Text to Image](../2%20-%20text-to-image/text-to-image.md) and [Image to Image](../3%20-%20image-to-image/image-to-image.md). Those use cases create or edit pixels; this one sends an existing image and receives text. The sample uses a local image, Microsoft Entra ID authentication, and the Responses API.

## What you need

1. A **Microsoft Foundry project** with a deployed vision-capable chat model, such as GPT-4o. Set `MODEL` to the exact deployment name from the project's **Deployed models** page.
2. **Azure CLI login** (`az login`) with permission to use the project, or another identity supported by `DefaultAzureCredential`.
3. Python 3.9 or later and the packages in [`code/requirements.txt`](code/requirements.txt).

Install the packages from the `code` folder:

```powershell
pip install -r requirements.txt
```

## How it works

The script:

1. Loads the project endpoint, deployment name, image path, and question from `.env`.
2. Authenticates with Microsoft Entra ID and connects to the project's OpenAI-compatible `/openai/v1` route. The local image stays local until its bytes are included in the HTTPS API request.
3. Encodes the image as a Base64 data URL and sends it with the text prompt to the Responses API.
4. Prints the model's text response and writes it to `output.txt`.

The request includes two content parts: a text instruction and an `input_image`. The `detail` setting controls the image-processing tradeoff: `high` is useful for small details and text, while `low` is faster and uses fewer image tokens.

```python
response = client.responses.create(
    model=MODEL,
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": PROMPT},
                {
                    "type": "input_image",
                    "image_url": f"data:{mime_type};base64,{encoded_image}",
                    "detail": DETAIL,
                },
            ],
        }
    ],
)

print(response.output_text)
```

## Configure and run it

From the `code` folder, copy the example settings and edit the values:

```powershell
Copy-Item .env.example .env
```

Set `PROJECT_ENDPOINT` to the project endpoint shown in Foundry, `MODEL` to your deployed vision model's exact deployment name, and `INPUT_FILE` to the image to analyze. Relative image paths are resolved from the `code` folder. The included `input.jpeg` is a sample image.

The script appends `/openai/v1` to the project endpoint to create the API base URL. Keep `PROJECT_ENDPOINT` as the project endpoint itself; don't add the API path in `.env`.

The sample's `.env.example` asks the model to describe the image. Change `PROMPT` to ask a specific question, for example, "What text is visible on the sign?" or "Summarize the main trend in this chart." `DETAIL` can be `auto`, `low`, or `high`.

Run the script from the `code` folder:

```powershell
python .\image_to_text.py
```

The answer appears in the terminal and is saved to `output.txt` in the code folder. Each run replaces that output file.

## Why use a vision-capable chat model?

The model needs to understand image content and produce a text answer. A vision-capable GPT deployment can caption a scene, answer questions about it, or read some visible text while responding to a natural-language prompt. The same request can be changed without training a custom image classifier.

Use the exact deployment name in `MODEL`; the model itself must support image input. Image-generation models such as those used in the text-to-image and image-to-image examples are not the right choice here because their purpose is to create or modify images, not to explain them.

For high-volume, exact OCR or document extraction, consider a purpose-built OCR or document-processing service instead. Vision models can misread small, rotated, dense, or stylized text, and their descriptions are not guaranteed to be exact.

## Microsoft Learn resources

- [Use the Azure OpenAI Responses API: image input](https://learn.microsoft.com/azure/foundry/openai/how-to/responses#image-input) — send image URLs or Base64-encoded image data to a vision-enabled model.
- [Use vision-enabled chat models](https://learn.microsoft.com/azure/foundry/openai/how-to/gpt-with-vision) — image input formats, detail settings, and limitations.
