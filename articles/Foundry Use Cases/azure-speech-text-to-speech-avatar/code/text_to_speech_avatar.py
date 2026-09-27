"""Create a talking-avatar MP4 with the Azure Speech batch synthesis REST API."""

import json
import os
import re
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import requests
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


HERE = Path(__file__).resolve().parent
API_VERSION = "2024-08-01"
POLL_INTERVAL_SECONDS = 10
MAX_WAIT_SECONDS = 15 * 60
SPEECH_SCOPE = "https://cognitiveservices.azure.com/.default"


class SpeechTokenAuth(requests.auth.AuthBase):
    def __init__(self) -> None:
        self.credential = DefaultAzureCredential()

    def __call__(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        request.headers["Authorization"] = (
            f"Bearer {self.credential.get_token(SPEECH_SCOPE).token}"
        )
        return request


def required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("<"):
        raise ValueError(f"Set {name} in code/.env before running this example.")
    return value


def speech_endpoint() -> str:
    endpoint = required_setting("PROJECT_ENDPOINT").rstrip("/")
    parts = urlsplit(endpoint)
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.port
        or parts.query
        or parts.fragment
    ):
        raise ValueError("PROJECT_ENDPOINT must be an HTTPS Foundry project or Speech resource URL.")
    if parts.hostname.endswith(".services.ai.azure.com"):
        if not re.fullmatch(r"/api/projects/[^/]+", parts.path):
            raise ValueError("PROJECT_ENDPOINT must include /api/projects/<project-name>.")
        resource = parts.hostname.removesuffix(".services.ai.azure.com")
        if not resource or "." in resource:
            raise ValueError("PROJECT_ENDPOINT has an invalid Foundry resource host.")
        return f"https://{resource}.cognitiveservices.azure.com"
    if parts.hostname.endswith(".cognitiveservices.azure.com") and not parts.path:
        return endpoint
    raise ValueError("PROJECT_ENDPOINT must be a Foundry project or Speech resource URL.")


def job_url(endpoint: str, job_id: str) -> str:
    return f"{endpoint}/avatar/batchsyntheses/{job_id}?api-version={API_VERSION}"


def submit_job(session: requests.Session, endpoint: str, text: str) -> str:
    job_id = f"avatar-{uuid.uuid4().hex}"
    payload = {
        "inputKind": "PlainText",
        "inputs": [{"content": text}],
        "synthesisConfig": {"voice": os.getenv("VOICE", "en-US-AvaMultilingualNeural")},
        "avatarConfig": {
            "talkingAvatarCharacter": os.getenv("AVATAR_CHARACTER", "lisa"),
            "talkingAvatarStyle": os.getenv("AVATAR_STYLE", "graceful-sitting"),
            "videoFormat": "mp4",
            "videoCodec": "h264",
        },
    }
    if len(json.dumps(payload).encode("utf-8")) > 500 * 1024:
        raise ValueError("The batch avatar request must be smaller than 500 KB.")
    response = session.put(job_url(endpoint, job_id), json=payload, timeout=30)
    response.raise_for_status()
    print(f"Submitted avatar job: {job_id}")
    return job_id


def wait_for_video(session: requests.Session, endpoint: str, job_id: str) -> str:
    deadline = time.monotonic() + MAX_WAIT_SECONDS
    while time.monotonic() < deadline:
        response = session.get(job_url(endpoint, job_id), timeout=30)
        response.raise_for_status()
        job = response.json()
        status = job["status"]
        print(f"Job {job_id}: {status}")
        if status == "Succeeded":
            video_url = job.get("outputs", {}).get("result")
            if not isinstance(video_url, str) or urlsplit(video_url).scheme != "https":
                raise RuntimeError(f"Job {job_id} succeeded without a valid HTTPS video URL.")
            return video_url
        if status in {"Failed", "Canceled", "Cancelled"}:
            raise RuntimeError(f"Job {job_id} ended with {status}: {job.get('properties', {}).get('error', job.get('error', 'No details'))}")
        if status not in {"NotStarted", "Running"}:
            raise RuntimeError(f"Job {job_id} returned an unexpected status: {status}")
        time.sleep(min(POLL_INTERVAL_SECONDS, max(0, deadline - time.monotonic())))
    raise TimeoutError(f"Job {job_id} did not finish in {MAX_WAIT_SECONDS // 60} minutes. Check its status later.")


def download_video(video_url: str, destination: Path) -> None:
    partial = destination.with_suffix(".mp4.part")
    try:
        # The output URL is signed; do not forward the Speech token to the storage host.
        with requests.get(video_url, stream=True, timeout=(10, 120)) as response:
            response.raise_for_status()
            with partial.open("wb") as output:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    output.write(chunk)
        partial.replace(destination)
    except (OSError, requests.RequestException):
        partial.unlink(missing_ok=True)
        raise


def main() -> None:
    if not load_dotenv(HERE / ".env", override=True):
        raise FileNotFoundError(f"Create {HERE / '.env'} from .env.example before running.")
    endpoint = speech_endpoint()
    text = (HERE / "prompt.txt").read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("Add some text to code/prompt.txt before running this example.")

    with requests.Session() as session:
        session.auth = SpeechTokenAuth()
        job_id = submit_job(session, endpoint, text)
        video_url = wait_for_video(session, endpoint, job_id)

    destination = HERE / f"{job_id}.mp4"
    download_video(video_url, destination)
    print(f"Saved video to {destination}")


if __name__ == "__main__":
    main()
