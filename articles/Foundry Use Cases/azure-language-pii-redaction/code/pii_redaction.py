import os
from pathlib import Path
from urllib.parse import urlsplit

import requests
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

API_VERSION = "2026-05-01"
TOKEN_SCOPE = "https://cognitiveservices.azure.com/.default"
DEFAULT_TEXT = "Please call Jane Doe at 555-123-4567 or email jane.doe@example.com."


def redact_text(project_endpoint: str, text: str) -> tuple[str, list[dict]]:
    project_url = urlsplit(project_endpoint)
    project_path = project_url.path.rstrip("/")
    project_name = project_path.removeprefix("/api/projects/")
    if (
        project_url.scheme != "https"
        or not project_url.netloc
        or project_url.username
        or project_url.password
        or project_url.query
        or project_url.fragment
        or not project_path.startswith("/api/projects/")
        or not project_name
        or "/" in project_name
        or "<" in project_endpoint
    ):
        raise ValueError(
            "Set PROJECT_ENDPOINT to the Foundry project URL "
            "(https://<resource>.services.ai.azure.com/api/projects/<project>)."
        )
    if not text.strip():
        raise ValueError("TEXT must not be empty.")

    resource_origin = f"{project_url.scheme}://{project_url.netloc}"
    with DefaultAzureCredential() as credential:
        token = credential.get_token(TOKEN_SCOPE).token
        response = requests.post(
            f"{resource_origin}/language/:analyze-text",
            params={"api-version": API_VERSION},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "kind": "PiiEntityRecognition",
                "parameters": {"modelVersion": "latest"},
                "analysisInput": {
                    "documents": [{"id": "1", "language": "en", "text": text}]
                },
            },
            timeout=30,
        )
        response.raise_for_status()

    results = response.json()["results"]
    if results.get("errors"):
        raise RuntimeError(f"Azure Language returned document errors: {results['errors']}")
    document = results["documents"][0]
    if document.get("id") != "1" or not isinstance(document.get("redactedText"), str):
        raise ValueError("Azure Language did not return redacted text for document 1.")
    return document["redactedText"], document["entities"]


if __name__ == "__main__":
    redacted, entities = redact_text(
        os.getenv("PROJECT_ENDPOINT", "").strip(),
        os.getenv("TEXT", DEFAULT_TEXT),
    )
    print("Redacted text:", redacted)
    print("Detected categories:", ", ".join(entity["category"] for entity in entities) or "none")
