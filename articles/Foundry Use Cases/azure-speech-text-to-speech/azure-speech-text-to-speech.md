---
title: "Text to Speech with Azure Speech in Microsoft Foundry"
excerpt: "Convert a text file to MP3 with Azure Speech in Foundry Tools, Python, the Speech SDK, and optional SSML voice controls."
slug: foundry-use-cases/azure-speech-text-to-speech
articleId: 747087d4-cc0a-4be4-816f-7f0417735577
artifactPath: "Foundry Use Cases/azure-speech-text-to-speech"
tags: ["Microsoft Foundry", "Azure Speech", "Python", "text to speech", "SSML"]
series: {"slug":"foundry-use-cases","title":"Microsoft Foundry - Use Cases","part":15}
publishAt: "2026-10-08T16:25:00.000Z"
---
# Getting Started: Text to Speech with Azure Speech in Microsoft Foundry

Azure Speech in Foundry Tools turns written text into spoken audio. This example reads a local text file, selects a neural voice, and saves an MP3. Unlike the [GPT Audio text-to-speech example](../5%20-%20text-to-speech/text-to-speech.md), it uses the dedicated **Azure Speech SDK** rather than an audio-capable chat model. No app server, model deployment name, or OpenAI client is needed.

## What you will build

A small Python script that reads `PROJECT_ENDPOINT` from `.env`, derives the Speech endpoint for the **same Foundry resource**, authenticates with Microsoft Entra ID, wraps your text in Speech Synthesis Markup Language (SSML), calls `SpeechSynthesizer.speak_ssml_async()`, and writes the returned MP3 bytes to a file. Optional settings let you change the voice, speaking style, rate, pitch, and volume.

## Prerequisites

- Python 3.10 or later.
- A Microsoft Foundry project whose **underlying Foundry resource also provides Azure Speech**, with the project endpoint (`https://<resource>.services.ai.azure.com/api/projects/<project>`). The project endpoint is not itself a Speech SDK endpoint. If Speech is on a separately connected resource, this minimal example cannot infer that resource's endpoint from the project URL.
- An identity that has the **Cognitive Services Speech User** (or **Cognitive Services Speech Contributor**) role on the Speech-capable resource. For local development, install Azure CLI and sign in with `az login`; `DefaultAzureCredential` also supports managed identities in Azure.
- Network access to that Speech resource. Synthesis may incur charges.

## Project files

- [`azure_speech_tts.py`](code/azure_speech_tts.py) - complete standalone Python script
- [`prompt.txt`](code/prompt.txt) - sample text to read aloud
- [`.env.example`](code/.env.example) - configuration template
- [`requirements.txt`](code/requirements.txt) - Speech SDK, Azure Identity, and dotenv

## Step 1: Install and configure

In the `code` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
az login
```

Edit `.env` and replace the placeholder with your **Foundry project** endpoint:

```dotenv
PROJECT_ENDPOINT=https://<your-foundry-resource>.services.ai.azure.com/api/projects/<your-project>
VOICE=en-US-AvaNeural
STYLE=
RATE=0%
PITCH=0%
VOLUME=0%
TEXT_FILE=prompt.txt
OUTPUT_FILE=speech.mp3
```

No API key is needed. `DefaultAzureCredential` uses your Azure CLI login locally (or another available Azure credential). You can also provide the settings as environment variables. The script resolves the input and output filenames relative to its own `code` folder, so it runs from any working directory. This endpoint conversion only applies when Speech is hosted by the **same** Foundry resource and uses the public Azure domain.

## Step 2: Choose the audio format

The script reads `PROJECT_ENDPOINT` and converts its resource hostname from `<resource>.services.ai.azure.com` to `<resource>.cognitiveservices.azure.com`. It rejects URLs that are not Foundry project URLs rather than sending the Speech request to an unrelated host. The Speech SDK then authenticates to that resource through `DefaultAzureCredential` instead of using a key. The output format is set *before* synthesis, so the bytes are encoded as MP3 rather than the SDK's default audio format:

```python
endpoint = speech_endpoint_from_project(required_setting("PROJECT_ENDPOINT"))
speech_config = speechsdk.SpeechConfig(
    token_credential=DefaultAzureCredential(), endpoint=endpoint
)
speech_config.set_speech_synthesis_output_format(
    speechsdk.SpeechSynthesisOutputFormat.Audio16Khz128KBitRateMonoMp3
)
```

You do not need a GPT Audio model deployment or a Foundry OpenAI endpoint for this call. If the project uses a *different* connected Speech resource, its endpoint cannot safely be inferred from `PROJECT_ENDPOINT`.

## Step 3: Customize speech with SSML

SSML is XML understood by the Speech service. `<voice>` chooses the speaker and `<prosody>` adjusts delivery. The example XML-escapes both the input text and attribute values so punctuation such as `&` or `<` does not break the request. When `STYLE` is set, the script wraps the prosody in `<mstts:express-as>`:

```xml
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
       xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="en-US">
  <voice name="en-US-AvaNeural">
    <prosody rate="0%" pitch="0%" volume="0%">Hello!</prosody>
  </voice>
</speak>
```

Leave `STYLE` empty to start. Speaking styles are voice-dependent: consult the [voice gallery and SSML guidance](https://learn.microsoft.com/azure/ai-services/speech-service/speech-synthesis-markup-voice) before setting a style such as `cheerful`. For a different language, choose an appropriate voice and update the `xml:lang` value in the script to match.

## Step 4: Synthesize and save

`audio_config=None` keeps the audio in the result instead of playing it over local speakers. A completed result contains `audio_data`; a canceled request includes cancellation details. The script only writes the MP3 after synthesis succeeds, avoiding a misleading empty output file.

```python
synthesizer = speechsdk.SpeechSynthesizer(
    speech_config=speech_config, audio_config=None
)
result = synthesizer.speak_ssml_async(ssml).get()
if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
    details = result.cancellation_details
    raise RuntimeError(
        f"Speech synthesis failed: {details.reason}; {details.error_details}"
    )
```

## Putting it all together

Save this as [`code/azure_speech_tts.py`](code/azure_speech_tts.py). It uses only `azure-cognitiveservices-speech`, `azure-identity`, `python-dotenv`, and the Python standard library. No imports or configuration from the larger application are required.

```python
"""Synthesize a text file to MP3 with Azure Speech in Foundry Tools."""

import html
import os
from pathlib import Path
from urllib.parse import urlsplit

import azure.cognitiveservices.speech as speechsdk
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")


def required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or (value.startswith("<") and value.endswith(">")):
        raise ValueError(f"Set {name} in {HERE / '.env'} or in your environment.")
    return value


def speech_endpoint_from_project(project_endpoint: str) -> str:
    parsed = urlsplit(project_endpoint)
    suffix = ".services.ai.azure.com"
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.netloc != parsed.hostname
        or not parsed.hostname.endswith(suffix)
        or parsed.query
        or parsed.fragment
        or len(parsed.path.rstrip("/").split("/")) != 4
        or not parsed.path.startswith("/api/projects/")
    ):
        raise ValueError(
            "PROJECT_ENDPOINT must be a Foundry project URL like "
            "https://<resource>.services.ai.azure.com/api/projects/<project>."
        )
    resource = parsed.hostname[: -len(suffix)]
    if not resource:
        raise ValueError("PROJECT_ENDPOINT must identify a Foundry resource.")
    return f"https://{resource}.cognitiveservices.azure.com/"


def main() -> None:
    endpoint = speech_endpoint_from_project(required_setting("PROJECT_ENDPOINT"))
    voice = os.getenv("VOICE", "en-US-AvaNeural").strip()
    style = os.getenv("STYLE", "").strip()
    rate = os.getenv("RATE", "0%").strip()
    pitch = os.getenv("PITCH", "0%").strip()
    volume = os.getenv("VOLUME", "0%").strip()
    if not voice:
        raise ValueError("VOICE cannot be empty.")

    text_path = HERE / os.getenv("TEXT_FILE", "prompt.txt")
    text = text_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"{text_path} is empty.")

    speech_config = speechsdk.SpeechConfig(
        token_credential=DefaultAzureCredential(), endpoint=endpoint
    )
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz128KBitRateMonoMp3
    )

    content = (
        f'<prosody rate="{html.escape(rate, quote=True)}" '
        f'pitch="{html.escape(pitch, quote=True)}" '
        f'volume="{html.escape(volume, quote=True)}">'
        f"{html.escape(text)}</prosody>"
    )
    if style:
        content = (
            f'<mstts:express-as style="{html.escape(style, quote=True)}">'
            f"{content}</mstts:express-as>"
        )
    ssml = (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        'xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="en-US">'
        f'<voice name="{html.escape(voice, quote=True)}">{content}</voice>'
        "</speak>"
    )

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=None
    )
    result = synthesizer.speak_ssml_async(ssml).get()
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        details = result.cancellation_details
        raise RuntimeError(
            f"Speech synthesis failed: {details.reason}; {details.error_details}"
        )
    if not result.audio_data:
        raise RuntimeError("Speech synthesis completed without audio.")

    output_path = HERE / os.getenv("OUTPUT_FILE", "speech.mp3")
    output_path.write_bytes(bytes(result.audio_data))
    print(f"Saved audio to {output_path}")


if __name__ == "__main__":
    main()
```

Edit `prompt.txt`, then run:

```powershell
python .\azure_speech_tts.py
```

Expected output (your path will vary):

```text
Saved audio to C:\...\code\speech.mp3
```

Open `speech.mp3` in an audio player. Missing credentials, insufficient Speech RBAC permissions, an unsupported voice/style, or a network failure raises an error instead of reporting success.

## What to try next

1. Change `VOICE` to another voice in the [supported voices list](https://learn.microsoft.com/azure/ai-services/speech-service/language-support?tabs=tts).
2. Set `RATE=10%` or `PITCH=-5%` and compare the generated audio.
3. Set `STYLE=cheerful` with a voice that supports that style.
4. Point `TEXT_FILE` at another UTF-8 file and generate a voiceover.

The key pattern is **SpeechConfig -> SSML -> SpeechSynthesizer -> audio bytes**. It scales from a one-file demo to applications that need predictable speech synthesis without a conversational model.

## Microsoft Learn resources

- [Speech synthesis with the Speech SDK](https://learn.microsoft.com/azure/ai-services/speech-service/how-to-speech-synthesis)
- [Microsoft Entra authentication with the Speech SDK](https://learn.microsoft.com/azure/ai-services/speech-service/how-to-configure-azure-ad-auth)
- [Text-to-speech quickstart](https://learn.microsoft.com/azure/ai-services/speech-service/get-started-text-to-speech)
- [SSML voice and style controls](https://learn.microsoft.com/azure/ai-services/speech-service/speech-synthesis-markup-voice)
