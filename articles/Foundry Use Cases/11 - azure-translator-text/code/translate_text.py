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
