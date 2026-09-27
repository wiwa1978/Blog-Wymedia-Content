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
