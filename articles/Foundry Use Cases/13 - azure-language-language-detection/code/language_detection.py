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
