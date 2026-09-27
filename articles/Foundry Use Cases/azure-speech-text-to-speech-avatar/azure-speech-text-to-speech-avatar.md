---
title: "Text to Speech Avatar with Azure Speech"
excerpt: "Turn a text script into a talking-avatar MP4 using Azure Speech batch synthesis, a small Python script, and the Speech REST API."
slug: foundry-use-cases/azure-speech-text-to-speech-avatar
articleId: f23315d5-9e52-408a-bc98-30d89e2e890a
artifactPath: "Foundry Use Cases/azure-speech-text-to-speech-avatar"
tags: ["Microsoft Foundry", "Azure Speech", "Python", "text to speech", "avatar"]
series: {"slug":"foundry-use-cases","title":"Microsoft Foundry - Use Cases","part":18}
publishAt: "2026-10-13T16:29:00.000Z"
---
# Getting Started: Text to Speech Avatar with Azure Speech in Microsoft Foundry

Suppose you have a short welcome message and want an on-screen presenter to read it aloud. Azure Speech text to speech avatar generates synchronized voice and video from the script. You can try the feature in the Microsoft Foundry playground; this guide shows the **batch REST API** behind a small, independent Python example.

This is **not** a conversational model, live WebRTC avatar, or the GPT audio completions API. Submit the complete text once, wait for the rendering job, and save the MP4 when it succeeds.

## What you will build

1. Read a script from `prompt.txt` and `PROJECT_ENDPOINT` from `.env`, and authenticate with Microsoft Entra ID.
2. Submit a batch avatar synthesis job using `PUT`.
3. Poll the job using `GET` until it succeeds or fails.
4. Download the resulting signed MP4 to your computer.

## Prerequisites

- Python 3.10 or later.
- An Azure subscription and a **paid Speech-capable Foundry resource** in a [region that supports batch avatars](https://learn.microsoft.com/azure/ai-services/speech-service/regions?tabs=ttsavatar). You can use the usual Foundry project URL in `.env`; the script derives the Speech endpoint for that resource. A separately connected Speech resource needs its own endpoint instead.
- Sign in with `az login` (or another identity supported by `DefaultAzureCredential`). Assign your identity the **Cognitive Services Speech User** or **Cognitive Services Speech Contributor** role on the resource serving Speech. No Speech key is needed.
- Access to the standard avatar `lisa` with the `graceful-sitting` style and a compatible Speech voice. The supplied `en-US-AvaMultilingualNeural` voice can be changed in `.env`.

Batch rendering is asynchronous and billable (avatar rendering and text-to-speech can be charged separately). The request payload limit is 500 KB, and output video length is limited to 20 minutes. Check [pricing](https://azure.microsoft.com/pricing/details/cognitive-services/speech-services/) and [current regional availability](https://learn.microsoft.com/azure/ai-services/speech-service/regions?tabs=ttsavatar) before running a large job.

## Project files

- [`text_to_speech_avatar.py`](code/text_to_speech_avatar.py) - standalone Python script
- [`prompt.txt`](code/prompt.txt) - script to read aloud
- [`.env.example`](code/.env.example) - configuration template
- [`requirements.txt`](code/requirements.txt) - `requests`, `python-dotenv`, and `azure-identity`
- [`README.md`](code/README.md) - quick run instructions
- [`test_text_to_speech_avatar.py`](code/test_text_to_speech_avatar.py) - offline request and download tests

## Step 1: Configure your Speech resource

Copy `code/.env.example` to `code/.env` and replace the placeholders:

```dotenv
PROJECT_ENDPOINT=https://<foundry-resource>.services.ai.azure.com/api/projects/<project-name>
VOICE=en-US-AvaMultilingualNeural
AVATAR_CHARACTER=lisa
AVATAR_STYLE=graceful-sitting
```

The code loads `PROJECT_ENDPOINT` from `.env`. For a URL such as `https://my-resource.services.ai.azure.com/api/projects/my-project`, it uses the Foundry resource hostname to construct `https://my-resource.cognitiveservices.azure.com` for the Speech REST call. The project URL itself does **not** serve batch avatar synthesis. This works when Speech is available on the **same resource**; it cannot discover a separately connected Speech resource or a different custom subdomain. In that case, put the direct `https://<speech-resource>.cognitiveservices.azure.com` URL in `PROJECT_ENDPOINT`.

`DefaultAzureCredential` obtains a token for `https://cognitiveservices.azure.com/.default` and attaches it as `Authorization: Bearer ...` to each Speech request. The credential refreshes tokens when needed during long jobs. An `AZURE_SPEECH_KEY` value left in an older `.env` is ignored; you can remove it.

## Step 2: Submit a batch video

Choose a unique job ID, then send the complete text and a standard character/style combination. `PlainText` requires `synthesisConfig.voice`:

```python
payload = {
    "inputKind": "PlainText",
    "inputs": [{"content": text}],
    "synthesisConfig": {"voice": voice},
    "avatarConfig": {
        "talkingAvatarCharacter": "lisa",
        "talkingAvatarStyle": "graceful-sitting",
        "videoFormat": "mp4",
        "videoCodec": "h264",
    },
}
response = session.put(
    f"{speech_endpoint}/avatar/batchsyntheses/{job_id}?api-version=2024-08-01",
    json=payload,
    timeout=30,
)
response.raise_for_status()
```

Here `session` is a `requests.Session` with Entra authentication, and `text`, `voice`, `speech_endpoint`, and `job_id` are initialized by the complete script below. The submission response reports a job status such as `NotStarted`; it does **not** contain the completed video.

## Step 3: Poll for a result

Call the same URL with `GET`. Expect `NotStarted` and `Running` while the job renders. On `Succeeded`, retrieve `outputs.result`; on `Failed` or a canceled job, surface the error instead of attempting a download.

```python
response = session.get(
    f"{speech_endpoint}/avatar/batchsyntheses/{job_id}?api-version=2024-08-01",
    timeout=30,
)
response.raise_for_status()
job = response.json()
if job["status"] == "Succeeded":
    video_url = job["outputs"]["result"]
```

The example waits between requests and stops after 15 minutes. If it times out, the submitted job may still finish in Azure; the printed ID can be used to query it later. A timeout does not cancel the job.

## Step 4: Download the MP4

The successful response provides a signed output URL. Stream its bytes to disk so you do not keep the entire video in memory:

```python
with requests.get(video_url, stream=True, timeout=(10, 120)) as response:
    response.raise_for_status()
    with open("avatar.mp4", "wb") as output:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            output.write(chunk)
```

The example deliberately uses a separate download request: **do not send the Speech bearer token to the video storage host**. Save the result promptly because the signed URL is temporary.

## Putting it all together

Save this complete script as `code/text_to_speech_avatar.py` (or use the [downloadable source](code/text_to_speech_avatar.py)). It adds endpoint and input validation, an overall polling deadline, error handling for failed jobs, and a partial download file that is renamed only after a successful transfer. There are no imports from the larger application.

```python
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
```

## Install and run

In PowerShell, change into this article's `code` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
az login
# Edit .env with your Foundry project endpoint; edit prompt.txt.
python .\text_to_speech_avatar.py
```

Here is the output from a successful run:

```text
PS C:\Code\Blog-Wymedia-Content\articles\Foundry Use Cases\18 - azure-speech-text-to-speech-avatar\code> python .\text_to_speech_avatar.py
Submitted avatar job: avatar-95ba936c22834052966c774a58fa3dce
Job avatar-95ba936c22834052966c774a58fa3dce: NotStarted
Job avatar-95ba936c22834052966c774a58fa3dce: Running
Job avatar-95ba936c22834052966c774a58fa3dce: Succeeded
Saved video to C:\Code\Blog-Wymedia-Content\articles\Foundry Use Cases\18 - azure-speech-text-to-speech-avatar\code\avatar-95ba936c22834052966c774a58fa3dce.mp4
```

## Watch the result

This is the generated video from that run. Press play to see **and hear** the avatar:

<video controls playsinline preload="metadata" width="720">
  <source src="video/avatar-demo.mp4" type="video/mp4">
  Your browser does not support embedded video.
</video>

[Download the sample MP4](video/avatar-demo.mp4) if the inline player does not work. The article copy is optimized for playback in a browser; the original output remains in `code` for local playback. The default Lisa/`graceful-sitting` pairing is a documented standard avatar. The simple script uses a standard voice and avatar; custom avatars and custom voices require their own configuration and, where applicable, Limited Access approval.

## What to try next

- Change `prompt.txt` and compare short scripts in different supported languages and voices.
- Try another [standard avatar and supported style](https://learn.microsoft.com/azure/ai-services/speech-service/text-to-speech-avatar/standard-avatars).
- Switch to SSML input to control pronunciation and pauses.
- Add background color, subtitles, or other [batch avatar properties](https://learn.microsoft.com/azure/ai-services/speech-service/text-to-speech-avatar/batch-synthesis-avatar-properties).
- Store the completed video in your own storage if viewers need durable access instead of a temporary signed URL.

Batch synthesis is a good fit for prepared training clips and announcements: the application submits a script, tracks a durable job ID, and downloads the finished asset. A real-time avatar is a different integration when you need a live conversation.

## Microsoft Learn resources

- [Use batch synthesis for text to speech avatar](https://learn.microsoft.com/azure/ai-services/speech-service/text-to-speech-avatar/batch-synthesis-avatar)
- [Speech REST API authentication](https://learn.microsoft.com/azure/ai-services/speech-service/rest-text-to-speech#authentication)
- [Microsoft Entra authentication and Speech resource roles](https://learn.microsoft.com/azure/ai-services/speech-service/how-to-configure-azure-ad-auth)
- [Microsoft Foundry SDKs and endpoints](https://learn.microsoft.com/azure/foundry/how-to/develop/sdk-overview#foundry-tools-sdks)
- [Text to speech avatar overview](https://learn.microsoft.com/azure/ai-services/speech-service/text-to-speech-avatar/what-is-text-to-speech-avatar)
- [Supported regions for Azure Speech](https://learn.microsoft.com/azure/ai-services/speech-service/regions?tabs=ttsavatar)
