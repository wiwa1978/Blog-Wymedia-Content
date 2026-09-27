---
title: "Extract detailed JSON from an image"
excerpt: "Analyze a local image with Azure Content Understanding's prebuilt-imageSearch analyzer and inspect the complete structured JSON result in Python."
slug: foundry-use-cases/context-extractor
articleId: 856ee824-c8bb-4ec4-b564-38bfe4e3d6a3
artifactPath: "Foundry Use Cases/context-extractor"
tags: ["Microsoft Foundry", "Azure AI", "Content Understanding", "Python", "image analysis"]
series: {"slug":"foundry-use-cases","title":"Microsoft Foundry - Use Cases","part":10}
publishAt: null
---
# Getting Started: Image to JSON with Azure Content Understanding

Azure Content Understanding can turn an image into structured information. This small Python sample uses the `prebuilt-imageSearch` analyzer from the Foundry playground's Python example. It reads **one local JPG or PNG**, waits for the analysis to finish, and prints the **entire analysis result as JSON**. There is no chat model, web server, or manual REST polling to set up.

`prebuilt-imageSearch` is meant for describing and understanding images, not for detailed OCR word coordinates. The **Document > Layout** playground uses a different analyzer (`prebuilt-layout`), which is why its JSON includes page geometry, individual words, and confidence scores. This guide focuses on Image Search only.

## What you need

1. A Microsoft Foundry resource in a region supporting Content Understanding, with the required [default model deployments configured](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/contentunderstanding/azure-ai-contentunderstanding#configuring-microsoft-foundry-resource).
2. The **Cognitive Services User** role on that resource and an identity available through `DefaultAzureCredential`; for local use, run `az login`.
3. Python 3.10 or later, a JPG or PNG image you are permitted to analyze, and the packages in [`code/requirements.txt`](code/requirements.txt).

## Step 1: Configure the project and authenticate

Run the following from this article's `code` directory. If you already created its `.venv`, simply activate it and install the updated requirements:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
az login
```

Set `PROJECT_ENDPOINT` in `.env` to the Foundry project URL you use in the other examples:

```dotenv
PROJECT_ENDPOINT=https://<resource-name>.services.ai.azure.com/api/projects/<project-name>
```

The SDK needs the **resource endpoint**, not the project URL. The script extracts `https://<resource-name>.services.ai.azure.com` from `PROJECT_ENDPOINT` before constructing `ContentUnderstandingClient`. Authentication uses `DefaultAzureCredential`; no API key is required. The pinned prerelease SDK supports the playground's `2026-06-01-preview` API.

## Step 2: Analyze local image bytes

The SDK's `begin_analyze_binary()` accepts local image bytes, unlike `begin_analyze()` in the playground's generated example, which takes an `AnalysisInput(url=...)`. The SDK handles the asynchronous operation and polling when you call `poller.result()`:

```python
from pathlib import Path

from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.identity import DefaultAzureCredential

with DefaultAzureCredential() as credential:
    with ContentUnderstandingClient(
        endpoint="https://<resource-name>.services.ai.azure.com",
        credential=credential,
        api_version="2026-06-01-preview",
    ) as client:
        poller = client.begin_analyze_binary(
            analyzer_id="prebuilt-imageSearch",
            binary_input=Path("input.png").read_bytes(),
            content_type="image/png",
        )
        result = poller.result()
```

The full script below validates the file and gets the endpoint from `.env`; it does not hardcode a resource name or image path.

## Step 3: Print the full structured result

`result.as_dict()` includes the analysis result's available content, metadata, fields, and warnings. `json.dumps(..., indent=2)` prints **all** of it, without the 50-line cutoff in the playground's generated example. This is the **analysis result**, not the outer operation envelope shown in the playground's Result tab: outer `id`, `status`, and `usage` are not necessarily in `result.as_dict()`.

## Putting it all together

The complete [`code/context_extractor.py`](code/context_extractor.py) is also available as a download:

```python
"""Analyze a local image with Azure Content Understanding and print detailed JSON."""

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

API_VERSION = "2026-06-01-preview"
IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}


def resource_endpoint(project_endpoint: str) -> str:
    parsed = urlsplit(project_endpoint.strip())
    parts = parsed.path.rstrip("/").split("/")
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or len(parts) != 4
        or parts[:3] != ["", "api", "projects"]
        or not parts[3]
        or "<" in project_endpoint
    ):
        raise ValueError(
            "Set PROJECT_ENDPOINT to https://<resource>.services.ai.azure.com"
            "/api/projects/<project>."
        )
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def analyze_image(image: Path, endpoint: str, credential: DefaultAzureCredential) -> dict:
    with ContentUnderstandingClient(
        endpoint=endpoint, credential=credential, api_version=API_VERSION
    ) as client:
        result = client.begin_analyze_binary(
            analyzer_id="prebuilt-imageSearch",
            binary_input=image.read_bytes(),
            content_type=IMAGE_TYPES[image.suffix.lower()],
        ).result()
    return result.as_dict()


def main() -> None:
    load_dotenv(Path(__file__).with_name(".env"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Local JPG or PNG image")
    args = parser.parse_args()
    image = args.image
    if not image.is_file() or image.suffix.lower() not in IMAGE_TYPES:
        parser.error("Choose an existing JPG or PNG image.")
    if not image.stat().st_size:
        parser.error("The image is empty.")
    try:
        endpoint = resource_endpoint(os.getenv("PROJECT_ENDPOINT", ""))
    except ValueError as exc:
        parser.error(str(exc))

    with DefaultAzureCredential() as credential:
        result = analyze_image(image, endpoint, credential)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

## Run it

From the `code` directory, use your own JPG or PNG; if `input.png` is present, you can start with it:

```powershell
python .\context_extractor.py .\input.png
```

To save the complete JSON instead of printing it in the terminal:

```powershell
python .\context_extractor.py .\input.png > .\image-result.json
```

Check `contents` for the image description and any extracted fields. The exact keys and values depend on the image and service version; a failed request raises an SDK exception rather than producing a success-shaped JSON result.

## What to try next

1. Compare results from a photograph and a chart to see how Image Search describes different visual content.
2. Read specific `contents` fields from the returned dictionary to feed a downstream search index.
3. For OCR word positions instead of image descriptions, try the separate `prebuilt-layout` analyzer.

The useful pattern is short: authenticate, submit local image bytes, wait for the SDK poller, and serialize the complete analysis result.

## Microsoft Learn resources

- [Azure Content Understanding Python SDK](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/contentunderstanding/azure-ai-contentunderstanding)
- [Prebuilt analyzers](https://learn.microsoft.com/azure/ai-services/content-understanding/concepts/prebuilt-analyzers)
