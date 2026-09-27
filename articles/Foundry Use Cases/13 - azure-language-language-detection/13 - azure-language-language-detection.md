---
title: "Detect text language with Azure Language"
excerpt: "Identify the predominant language of text with Azure Language's REST API, Python, and keyless Microsoft Entra authentication."
slug: foundry-use-cases/azure-language-language-detection
articleId: c066986a-3f95-48c2-9e3f-a45ae9556796
artifactPath: "Foundry Use Cases/13 - azure-language-language-detection"
tags: ["Microsoft Foundry", "Azure Language", "Python", "language detection"]
series: {"slug":"foundry-use-cases","title":"Microsoft Foundry - Use Cases","part":12}
publishAt: null
---
# Getting Started: Detect Text Language with Azure Language in Microsoft Foundry

When an application accepts text in several languages, it helps to identify the input language before routing it to a translator or another workflow. Azure Language in Foundry Tools can return the **predominant language**, its ISO 639-1 code, and a confidence score. This example is one independent REST call, not a chat-model prompt or deployment.

## Prerequisites

1. An Azure Language-enabled Foundry/Azure AI Services resource and a Foundry project on it. Copy its **project endpoint**, for example `https://<resource-name>.services.ai.azure.com/api/projects/<project-name>`. The script extracts the resource origin for the Language REST API.
2. An identity with permission to call that resource, such as the **Cognitive Services User** role. For local development, install Azure CLI and run `az login`; `DefaultAzureCredential` can use a managed identity in Azure instead.
3. Python 3.10 or later and the packages in [`code/requirements.txt`](code/requirements.txt). No API key or model deployment name is needed.

## Step 1: Authenticate

Request a Microsoft Entra token for the Cognitive Services scope. The script attaches it to the HTTP `Authorization` header without storing credentials in the article:

```python
from azure.identity import DefaultAzureCredential

with DefaultAzureCredential() as credential:
    token = credential.get_token("https://cognitiveservices.azure.com/.default").token
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
```

Set `PROJECT_ENDPOINT` in `.env` to your Foundry project URL. Azure Language uses the **resource origin**, not `/api/projects/<project-name>`: the program removes the project path before appending `/language/:analyze-text` and `api-version=2026-05-01`.

## Step 2: Describe the text

Set `kind` to `LanguageDetection`, give the document an ID, and include its text. Do **not** supply a document `language` field: finding that language is the point of the call.

```json
{
  "kind": "LanguageDetection",
  "parameters": {"modelVersion": "latest"},
  "analysisInput": {
    "documents": [{"id": "1", "text": "Ce restaurant offre un service excellent."}]
  }
}
```

## Step 3: Read the response

`POST` the JSON to `{endpoint}/language/:analyze-text?api-version=2026-05-01`. For a successful single-document request, inspect `results.documents[0].detectedLanguage`:

```json
{
  "kind": "LanguageDetectionResults",
  "results": {
    "documents": [{
      "id": "1",
      "detectedLanguage": {
        "name": "French",
        "iso6391Name": "fr",
        "confidenceScore": 0.98
      },
      "warnings": []
    }],
    "errors": []
  }
}
```

This response is illustrative; confidence scores vary. The API returns a fraction (here `0.98`); the script displays it as a percentage (`98%`). The script checks both HTTP failures and `results.errors`, because the service can report document-level errors separately. Short, ambiguous, numeric-only, or mixed-language text may return lower confidence or `(Unknown)` rather than a reliable routing signal.

## Putting it all together

The complete standalone program is [`code/language_detection.py`](code/language_detection.py). It loads [`code/.env.example`](code/.env.example) after you copy it to `.env`:

```python
"""Detect the predominant language of a text with Azure Language."""

import os
from pathlib import Path
from urllib.parse import urlsplit

import requests
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

API_VERSION = "2026-05-01"
TOKEN_SCOPE = "https://cognitiveservices.azure.com/.default"


def language_endpoint(project_endpoint: str) -> str:
    parsed = urlsplit(project_endpoint.strip())
    segments = parsed.path.strip("/").split("/")
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or len(segments) != 3
        or segments[:2] != ["api", "projects"]
        or not segments[2]
    ):
        raise ValueError("Set PROJECT_ENDPOINT to the HTTPS Foundry project URL.")
    return f"{parsed.scheme}://{parsed.netloc}"


def detect_language(endpoint: str, token: str, text: str) -> tuple[str, str, float]:
    response = requests.post(
        f"{endpoint.rstrip('/')}/language/:analyze-text",
        params={"api-version": API_VERSION},
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
        },
        json={
            "kind": "LanguageDetection",
            "parameters": {"modelVersion": "latest"},
            "analysisInput": {"documents": [{"id": "1", "text": text}]},
        },
        timeout=30,
    )
    response.raise_for_status()
    results = response.json()["results"]
    if results.get("errors"):
        raise RuntimeError(f"Language detection failed: {results['errors']}")
    documents = results["documents"]
    if len(documents) != 1 or documents[0]["id"] != "1":
        raise ValueError("Azure Language did not return document 1.")
    detected = documents[0]["detectedLanguage"]
    return detected["name"], detected["iso6391Name"], detected["confidenceScore"]


def main() -> None:
    load_dotenv(Path(__file__).with_name(".env"))
    endpoint = language_endpoint(os.getenv("PROJECT_ENDPOINT", ""))
    text = os.getenv("TEXT", "").strip()
    if not text:
        raise ValueError("Set TEXT to a non-empty text sample.")

    with DefaultAzureCredential() as credential:
        token = credential.get_token(TOKEN_SCOPE).token
        name, code, confidence = detect_language(endpoint, token, text)
    print(f"Detected language: {name} ({code}), confidence {confidence:.0%}")


if __name__ == "__main__":
    main()
```

## Configure and run

In PowerShell, starting in this article's `code` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
az login
python .\language_detection.py
```

Edit `.env` before running: replace `PROJECT_ENDPOINT` with your own Foundry project endpoint, and optionally change `TEXT`. The script calls Azure Language at the resource origin from that URL. An example result is `Detected language: French (fr), confidence 98%`; actual values depend on the input. Keep `.env` local. For 401/403 errors, check the identity's resource role; for 404, check the project endpoint's resource origin and Language capability.

## What to try next

1. Try a longer text sample in another [supported language](https://learn.microsoft.com/azure/ai-services/language-service/language-detection/language-support).
2. Test ambiguous single words versus complete sentences; compare the confidence scores.
3. Add a `countryHint` to the document when you know its likely region, and see how ambiguous results change.
4. Send several documents in one `analysisInput.documents` list and match each response by `id` before routing.

The reusable pattern is **authenticate, submit a document, then inspect its detected language and confidence**. It lets you make an informed routing decision without bringing in a larger application or deploying a chat model.

## Microsoft Learn resources

- [Language detection quickstart](https://learn.microsoft.com/azure/ai-services/language-service/language-detection/quickstart)
- [How to use language detection](https://learn.microsoft.com/azure/ai-services/language-service/language-detection/how-to/call-api)
- [Analyze Text REST API](https://learn.microsoft.com/rest/api/language/analyze-text/analyze-text/analyze-text?view=rest-language-analyze-text-2026-05-01)
