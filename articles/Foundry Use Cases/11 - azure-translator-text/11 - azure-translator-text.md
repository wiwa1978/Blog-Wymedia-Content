---
title: "Translate text with Azure Translator"
excerpt: "Translate one piece of text into multiple languages with Azure Translator's REST API, Python, and keyless Microsoft Entra authentication."
slug: foundry-use-cases/azure-translator-text
articleId: 28d12876-6b8d-49fc-b27b-b37e30572fa9
artifactPath: "Foundry Use Cases/11 - azure-translator-text"
tags: ["Microsoft Foundry", "Azure Translator", "Python", "translation"]
series: {"slug":"foundry-use-cases","title":"Microsoft Foundry - Use Cases","part":11}
publishAt: "2026-10-05T16:16:00.000Z"
---
# Getting Started: Translate Text with Azure Translator in Microsoft Foundry

Azure Translator is a purpose-built translation service in Foundry Tools. Unlike prompting a chat model to translate, its text API accepts target language codes and can return several translations in one request. This example uses standard neural machine translation (NMT), not a GPT deployment or the older Translator v3.0 payload.

## Prerequisites

- A Translator-capable Foundry resource and its **project endpoint** (for example, `https://my-resource.services.ai.azure.com/api/projects/my-project`). The script derives the Translator endpoint for that same resource; a project endpoint is not itself a Translator API URL.
- An identity with the **Cognitive Services User** role on that resource. Run `az login` locally, or use another identity supported by `DefaultAzureCredential`.
- Python 3.10 or newer, Azure CLI, and the packages in [`code/requirements.txt`](code/requirements.txt).

No model deployment name or resource key is needed for this keyless NMT example. Edit [`code/input.txt`](code/input.txt) to choose the text to translate; the script reads it as UTF-8 from its own folder, even when invoked from another working directory.

## Step 1: Authenticate and choose the endpoint

The script gets a Microsoft Entra token for the Cognitive Services scope. It derives `https://my-resource.cognitiveservices.azure.com` from `PROJECT_ENDPOINT` on `https://my-resource.services.ai.azure.com/api/projects/my-project`, then sends the token to that resource-specific URL. The `/translator/text/translate` path and `api-version=2026-06-06` select the current GA text translation API.

```python
from azure.identity import DefaultAzureCredential

with DefaultAzureCredential() as credential:
    token = credential.get_token(
        "https://cognitiveservices.azure.com/.default"
    ).token
```

Keep the Foundry project URL in `.env`; the script checks its shape, swaps the resource host suffix, and appends the REST path. Use the project on the **same resource** that has Translator enabled. The API version here uses the new `inputs`/`value` schema; don't mix it with v3.0's array body and `to` query parameter.

## Step 2: Read the input and send the targets

A request has one `inputs` entry with the content of `input.txt` and an array of target language codes. Multiline text is supported; surrounding whitespace is removed. Omit `language` to let Translator detect the source. Set `SOURCE_LANGUAGE=en` if you know the input is English.

```json
{
  "inputs": [
    {
      "text": "Hello, welcome to our website!",
      "targets": [{"language": "fr"}, {"language": "de"}]
    }
  ]
}
```

`requests.post(..., json=...)` serializes this payload and the bearer token goes in the `Authorization` header. Language codes must be supported by Translator; see the [supported languages](https://learn.microsoft.com/azure/ai-services/language-support).

## Step 3: Read the translations

For a single input, `value[0].translations` contains one entry per requested target. When the source was auto-detected, `value[0].detectedLanguage.language` reports it:

```json
{
  "value": [
    {
      "detectedLanguage": {"language": "en", "score": 1.0},
      "translations": [
        {"language": "fr", "text": "Bonjour, bienvenue sur notre site Web!"},
        {"language": "de", "text": "Hallo, willkommen auf unserer Website!"}
      ]
    }
  ]
}
```

Translations can vary; this is an illustrative response, not an exact-output assertion.

## Putting it all together

Save the following as `translate_text.py`, or download the identical [`code/translate_text.py`](code/translate_text.py):

```python
"""Translate one text into several languages with Azure Translator."""

import os
from pathlib import Path
from urllib.parse import urlsplit

import requests
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

API_VERSION = "2026-06-06"
TOKEN_SCOPE = "https://cognitiveservices.azure.com/.default"


def translator_endpoint_from_project(project_endpoint: str) -> str:
    parsed = urlsplit(project_endpoint.strip().rstrip("/"))
    hostname = parsed.hostname or ""
    resource_name = hostname.removesuffix(".services.ai.azure.com")
    if (
        parsed.scheme != "https"
        or parsed.netloc != hostname
        or not hostname.endswith(".services.ai.azure.com")
        or not resource_name
        or "." in resource_name
        or not parsed.path.startswith("/api/projects/")
        or not parsed.path[len("/api/projects/") :]
        or "/" in parsed.path[len("/api/projects/") :]
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Set PROJECT_ENDPOINT to a Foundry project HTTPS endpoint")
    return f"https://{resource_name}.cognitiveservices.azure.com"


def load_input_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Add text to {path.name} before translating")
    return text


def translate(
    endpoint: str,
    token: str,
    text: str,
    targets: list[str],
    source: str | None = None,
) -> tuple[str | None, list[tuple[str, str]]]:
    item = {"text": text, "targets": [{"language": language} for language in targets]}
    if source:
        item["language"] = source

    response = requests.post(
        f"{endpoint.rstrip('/')}/translator/text/translate",
        params={"api-version": API_VERSION},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"inputs": [item]},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()
    try:
        first = result["value"][0]
        translations = [
            (entry["language"], entry["text"]) for entry in first["translations"]
        ]
        if not translations:
            raise ValueError("Translator returned no translations")
        detected = first.get("detectedLanguage")
        detected_language = detected["language"] if detected else None
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Unexpected Translator response shape") from exc
    return detected_language, translations


def main() -> None:
    load_dotenv(Path(__file__).with_name(".env"))
    project_endpoint = os.getenv("PROJECT_ENDPOINT", "")
    endpoint = translator_endpoint_from_project(project_endpoint)
    text = load_input_text(Path(__file__).with_name("input.txt"))
    targets = [
        language.strip()
        for language in os.getenv("TARGET_LANGUAGES", "").split(",")
        if language.strip()
    ]
    source = os.getenv("SOURCE_LANGUAGE", "").strip() or None

    if not targets:
        raise ValueError("Set at least one TARGET_LANGUAGES code in .env")

    with DefaultAzureCredential() as credential:
        token = credential.get_token(TOKEN_SCOPE).token
        detected, translations = translate(endpoint, token, text, targets, source)

    print(f"Source: {source or detected or 'not reported'}")
    for language, translated_text in translations:
        print(f"{language}: {translated_text}")


if __name__ == "__main__":
    main()
```

## Configure and run

In PowerShell, from the article's `code` folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
az login
python .\translate_text.py
```

Edit `.env` before the last command: set `PROJECT_ENDPOINT` to your Foundry project URL (not the Translator resource URL) and comma-separated `TARGET_LANGUAGES` as desired. Edit `input.txt` in the same `code` folder to change the text being translated; the sample file already contains a short sentence. There is no `TRANSLATOR_ENDPOINT` or `TEXT` setting. Leave `SOURCE_LANGUAGE` empty for automatic detection. The output is printed to the terminal (for example, `Source: en`, `fr: ...`, `de: ...`). A missing or empty input file raises an error before any API request. Keep `.env` local even though this example contains no secrets.

## What to try next

1. Change `TARGET_LANGUAGES` to `es,it,nl` to translate the same input into three other languages.
2. Supply `SOURCE_LANGUAGE` and compare results with auto-detection for short or ambiguous text.
3. Send multiple `inputs` entries in one request and iterate over the matching `value` results.
4. Compare NMT with a supported LLM translation deployment by adding a documented `deploymentName` to each target (requires a Foundry resource).

The underlying pattern is a small, authenticated REST call: provide text and targets, then map each returned translation to its language. It works independently of a web application or chat-model pipeline.

## Microsoft Learn resources

- [Text translation API (2026-06-06)](https://learn.microsoft.com/azure/ai-services/translator/text-translation/2026-06-06/translate-api) — endpoint, request and response contract.
- [Translator authentication and authorization](https://learn.microsoft.com/azure/ai-services/translator/text-translation/reference/authentication) — Microsoft Entra ID and resource-specific endpoints.
- [Azure text translation overview](https://learn.microsoft.com/azure/ai-services/translator/text-translation/overview) — API versions, NMT/LLM differences and limits.
