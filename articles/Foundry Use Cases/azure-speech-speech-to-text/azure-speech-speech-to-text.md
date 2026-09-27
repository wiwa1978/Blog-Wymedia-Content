---
title: "Live speech to text with Azure Speech"
excerpt: "Transcribe a microphone continuously with Azure Speech in Foundry Tools, print completed utterances, and save the transcript using a standalone Python script."
slug: foundry-use-cases/azure-speech-speech-to-text
articleId: fdcbef2c-f5cf-439f-a3e9-a05a77ea2460
artifactPath: "Foundry Use Cases/azure-speech-speech-to-text"
tags: ["Microsoft Foundry", "Azure Speech", "Python", "speech to text", "microphone"]
series: {"slug":"foundry-use-cases","title":"Microsoft Foundry - Use Cases","part":16}
publishAt: "2026-10-10T16:26:00.000Z"
---
# Getting Started: Live Speech to Text with Azure Speech in Microsoft Foundry

Turn speech from your microphone into text as you speak. This small Python program uses **Azure Speech in Foundry Tools** for continuous recognition: it captures live audio from your **default microphone**, prints each completed utterance, and saves the transcript to a text file. It does not read `speech.mp3` or save a recording of the audio. There is no web server, browser, or application framework to set up.

This is different from [live microphone transcription with a Foundry Realtime model](../9%20-%20audio-transcription-microphone/audio-transcription-microphone.md). That example streams raw microphone chunks to a model over a WebSocket. Here the **Speech SDK** captures the microphone and manages streaming to the **Speech service**. Both approaches can authenticate with Microsoft Entra ID; the Speech SDK uses the Speech resource endpoint, which this sample derives from a Foundry project endpoint when both are on the same resource.

## Prerequisites

- A Speech-enabled Foundry resource and its **project endpoint** (`https://<resource>.services.ai.azure.com/api/projects/<project>`). If Speech is on another resource, use that resource's Speech endpoint from **Keys and Endpoint** instead.
- A signed-in identity supported by `DefaultAzureCredential` (for example, `az login`) with the **Cognitive Services Speech User** or **Cognitive Services Speech Contributor** role on that resource. No API key is required.
- Python and a working default microphone with microphone access enabled for your terminal.
- The three packages in [`code/requirements.txt`](code/requirements.txt): `azure-cognitiveservices-speech`, `azure-identity`, and `python-dotenv`.

The standalone project contains [`speech_to_text.py`](code/speech_to_text.py), [`requirements.txt`](code/requirements.txt), [`.env.example`](code/.env.example), and [`README.md`](code/README.md).

## Step 1: Configure the Speech service

Copy [`code/.env.example`](code/.env.example) to `code/.env` and replace the placeholders:

```dotenv
PROJECT_ENDPOINT=https://<resource-name>.services.ai.azure.com/api/projects/<project-name>
SPEECH_LANGUAGE=en-US
OUTPUT_TXT=output.txt
```

The sample reads `PROJECT_ENDPOINT` from `.env`. Given `https://my-resource.services.ai.azure.com/api/projects/my-project`, it derives `https://my-resource.cognitiveservices.azure.com` for the Speech SDK. This hostname conversion only identifies the right Speech endpoint when **Speech is enabled on the same Foundry resource**. If it is on a separate resource, set `PROJECT_ENDPOINT` to that resource's direct `https://<speech-resource>.cognitiveservices.azure.com/` endpoint instead. The Speech SDK uses `DefaultAzureCredential` to obtain a Microsoft Entra token for the Speech service; the source application's Realtime WebSocket uses a different token audience (`https://ai.azure.com/.default`). Use a supported locale such as `en-US` or `fr-FR` for `SPEECH_LANGUAGE`.

## Step 2: Capture microphone audio

Create the Speech configuration, select the recognition language, and use the machine's default microphone:

```python
import os
from urllib.parse import urlsplit

import azure.cognitiveservices.speech as speechsdk
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()
project_host = urlsplit(os.environ["PROJECT_ENDPOINT"]).hostname
resource_name = project_host.removesuffix(".services.ai.azure.com")
speech_endpoint = f"https://{resource_name}.cognitiveservices.azure.com"
credential = DefaultAzureCredential()
speech_config = speechsdk.SpeechConfig(
    token_credential=credential, endpoint=speech_endpoint
)
speech_config.speech_recognition_language = "en-US"
audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
recognizer = speechsdk.SpeechRecognizer(
    speech_config=speech_config, audio_config=audio_config
)
```

The SDK handles microphone capture and audio transport. Unlike the Realtime-model example, you do not need to resample PCM audio, encode chunks, or proxy a WebSocket.

## Step 3: Listen for completed utterances

Continuous recognition emits events rather than returning one final result. Add the following after the setup in Step 2 to receive final text; the full script below also listens for `canceled` to detect service errors and `session_stopped` to detect the end of the session:

```python
def on_recognized(event):
    if event.result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print(f"Recognized: {event.result.text}")

recognizer.recognized.connect(on_recognized)
try:
    recognizer.start_continuous_recognition_async().get()
    input("Speak, then press Enter to stop...")
finally:
    recognizer.stop_continuous_recognition_async().get()
    credential.close()
```

For live subtitles, you can also subscribe to `recognizing` for **interim** text. Do not save interim text as a final transcript: it may change before the `recognized` event arrives.

## Putting it all together

Save this complete script as `code/speech_to_text.py` (the linked sample already contains it):

```python
"""Transcribe the default microphone with Azure Speech in Foundry Tools."""

import os
import re
import threading
from pathlib import Path
from urllib.parse import urlsplit

import azure.cognitiveservices.speech as speechsdk
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")


def required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("<"):
        raise ValueError(f"Set {name} in {SCRIPT_DIR / '.env'} before running.")
    return value


def speech_endpoint() -> str:
    endpoint = required_setting("PROJECT_ENDPOINT").rstrip("/")
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
        or parsed.port
    ):
        raise ValueError(
            "PROJECT_ENDPOINT must be an HTTPS Foundry project or Speech resource URL."
        )
    if parsed.hostname.endswith(".cognitiveservices.azure.com") and not parsed.path:
        return endpoint
    if parsed.hostname.endswith(".services.ai.azure.com") and re.fullmatch(
        r"/api/projects/[^/]+", parsed.path
    ):
        resource = parsed.hostname.removesuffix(".services.ai.azure.com")
        if resource and "." not in resource:
            return f"https://{resource}.cognitiveservices.azure.com"
    raise ValueError(
        "PROJECT_ENDPOINT must be a Foundry URL like "
        "https://<resource>.services.ai.azure.com/api/projects/<project> "
        "or a Speech URL like https://<resource>.cognitiveservices.azure.com."
    )


def main() -> None:
    with DefaultAzureCredential() as credential:
        speech_config = speechsdk.SpeechConfig(
            token_credential=credential,
            endpoint=speech_endpoint(),
        )
        speech_config.speech_recognition_language = os.getenv("SPEECH_LANGUAGE", "en-US")
        audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_config
        )

        done = threading.Event()
        transcripts: list[str] = []
        errors: list[str] = []

        def on_recognized(event) -> None:
            if event.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                transcripts.append(event.result.text)
                print(f"\nRecognized: {event.result.text}", flush=True)

        def on_canceled(event) -> None:
            if event.reason == speechsdk.CancellationReason.Error:
                errors.append(event.error_details)
            done.set()

        recognizer.recognized.connect(on_recognized)
        recognizer.canceled.connect(on_canceled)
        recognizer.session_stopped.connect(lambda event: done.set())

        try:
            recognizer.start_continuous_recognition_async().get()
            print("Listening... speak into your microphone. Press Ctrl+C to stop.")
            while not done.wait(0.2):
                pass
        except KeyboardInterrupt:
            print("\nStopped.")
        finally:
            recognizer.stop_continuous_recognition_async().get()

    if errors:
        raise RuntimeError(f"Speech recognition failed: {errors[0]}")

    if transcripts:
        output = SCRIPT_DIR / os.getenv("OUTPUT_TXT", "output.txt")
        output.write_text("\n".join(transcripts) + "\n", encoding="utf-8")
        print(f"Saved transcript to {output}")
    else:
        print("No speech was recognized.")


if __name__ == "__main__":
    main()
```

The callback saves only final recognized utterances. If the service cancels because of an error, the script reports the error instead of quietly treating it as a successful empty transcript.

## Run it

Open PowerShell in this article's `code` folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env with your Foundry project endpoint.
az login
python .\speech_to_text.py
```

Speak into the **default microphone** and pause between sentences. Press `Ctrl+C` to stop. Here is output from a sample run:

```text
Listening... speak into your microphone. Press Ctrl+C to stop.

Stopped.

Recognized: Hi there this is a test to check that everything works.
Saved transcript to C:\Code\Blog-Wymedia-Content\articles\Foundry Use Cases\16 - azure-speech-speech-to-text\code\output.txt
```

The final recognized utterance can appear after `Stopped.` because the Speech SDK finishes processing buffered microphone audio while it stops. Only the transcript is saved to `output.txt`; no MP3 or WAV file is created.

If recognition is canceled with an authentication error, confirm that your signed-in identity has the **Cognitive Services Speech User** role on the Speech resource and that it is the **same resource** identified by your Foundry project endpoint. If the microphone cannot open, check operating-system microphone permissions and the default recording device.

## What to try next

1. Change `SPEECH_LANGUAGE` to another [supported locale](https://learn.microsoft.com/azure/ai-services/speech-service/language-support), such as `nl-BE`.
2. Subscribe to `recognizing` for provisional live captions while retaining `recognized` for the saved transcript.
3. Replace the microphone with `speechsdk.audio.AudioConfig(filename="recording.wav")` to recognize a local WAV file.
4. Add timestamps or speaker identification when your scenario needs more than plain text.

Continuous recognition is the useful building block here: the Speech SDK handles the live audio stream, while your program decides how to display and store final results.

## Microsoft Learn resources

- [How to recognize speech with Azure Speech](https://learn.microsoft.com/azure/ai-services/speech-service/how-to-recognize-speech)
- [Speech to text quickstart](https://learn.microsoft.com/azure/ai-services/speech-service/get-started-speech-to-text)
- [Speech SDK for Python](https://learn.microsoft.com/python/api/overview/azure/cognitiveservices-speech-readme)
- [Microsoft Entra authentication with the Speech SDK](https://learn.microsoft.com/azure/ai-services/speech-service/how-to-configure-azure-ad-auth)
- [Microsoft Foundry SDKs and endpoints](https://learn.microsoft.com/azure/foundry/how-to/develop/sdk-overview)
