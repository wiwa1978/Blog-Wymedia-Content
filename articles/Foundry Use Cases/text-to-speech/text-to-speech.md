---
title: "Text to Speech"
excerpt: "Turn written text into natural-sounding speech using Microsoft Foundry audio completions, Python, Entra ID authentication, and the OpenAI-compatible chat completions API with the audio modality."
slug: foundry-use-cases/text-to-speech
articleId: 685b19d3-bd8a-4c25-9673-dfea3d152b0c
artifactPath: "Foundry Use Cases/text-to-speech"
tags: ["Microsoft Foundry", "Azure AI", "Python", "text to speech"]
series: {"slug":"foundry-use-cases","title":"Microsoft Foundry - Use Cases","part":4}
publishAt: "2026-09-27T14:48:00.000Z"
---
# Text to speech with Microsoft Foundry audio completions

Microsoft Foundry audio-enabled models can turn written text into natural-sounding speech. This small Python example uses the chat completions API with the audio modality, then writes the returned MP3 bytes to a local file.

The sample is based on the GPT Audio implementation used by the larger Foundry Chat App. It deliberately keeps the text-to-speech instruction separate from the text being read: the model is asked to speak the input verbatim rather than answer or summarize it.

## What you will build

The script:

1. Authenticates with `DefaultAzureCredential`.
2. Derives the project OpenAI endpoint from `PROJECT_ENDPOINT`.
3. Reads the text to speak from `prompt.txt` (or `TEXT` in `.env`).
4. Sends text with `modalities=["text", "audio"]`.
5. Selects a voice and MP3 output format.
6. Decodes the base64 audio response and saves a timestamped `.mp3` file.

## Prerequisites

- A Microsoft Foundry project.
- An audio-enabled model deployment, such as `gpt-4o-mini-audio-preview`.
- Azure credentials available to `DefaultAzureCredential` (for example, an authenticated Azure CLI session).
- Python 3.10 or later.

`MODEL` must be the exact deployment name from the Foundry **Models + endpoints** page. A base model name and a deployment name are not always the same.

## Project files

- [`text_to_speech.py`](code/text_to_speech.py) — runnable example
- [`prompt.txt`](code/prompt.txt) — text read aloud by default
- [`.env.example`](code/.env.example) — configuration template
- [`requirements.txt`](code/requirements.txt) — Python dependencies

Clicking the code link opens the source in the site’s code modal; it can also be downloaded from there.

## Configuration

Copy `.env.example` to `.env` and set the project endpoint and deployment:

```dotenv
PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
MODEL=gpt-4o-mini-audio-preview
VOICE=alloy
TEXT=
TEXT_FILE=prompt.txt
OUTPUT_FILE=speech
```

By default, the script reads the text to speak from `prompt.txt`. Edit that file to change what's read aloud, or set `TEXT` in `.env` to override it — `TEXT` takes precedence over `TEXT_FILE` when both are set.

The output name is generated as:

```text
speech_<MODEL>_<YYYYMMDD_HHMMSS>.mp3
```

For example:

```text
speech_gpt-4o-mini-audio-preview_20260417_153000.mp3
```

## Install and run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python .\text_to_speech.py
```

Expected terminal output:

```text
Saved audio to speech_gpt-4o-mini-audio-preview_20260417_153000.mp3
```

Open the generated MP3 file in any audio player.

## The core request

```python
response = client.chat.completions.create(
    model=MODEL,
    modalities=["text", "audio"],
    audio={"voice": VOICE, "format": "mp3"},
    messages=[
        {
            "role": "system",
            "content": (
                "You are a text-to-speech engine. Read the user's text aloud "
                "verbatim. Do not answer it, paraphrase it, or add any words."
            ),
        },
        {"role": "user", "content": text},
    ],
)

audio = base64.b64decode(response.choices[0].message.audio.data)
Path(output_path).write_bytes(audio)
```

The response contains audio data as base64. Decoding it produces the binary MP3 content that can be saved or streamed to an application.

## Choosing a voice and format

Audio completions support voices including `alloy`, `ash`, `ballad`, `coral`, `echo`, `sage`, `shimmer`, `verse`, `marin`, and `cedar`, subject to the deployed model and API version. The example uses `alloy`. MP3 is convenient for a small downloadable file; the service also supports formats such as WAV, FLAC, OPUS, PCM16, and AAC.

## Microsoft Learn resources

- [Quickstart: Get started with Azure OpenAI audio generation](https://learn.microsoft.com/azure/foundry/openai/audio-completions-quickstart)
- [Audio capabilities in Azure OpenAI](https://learn.microsoft.com/azure/foundry-classic/openai/concepts/audio)
- [Microsoft Foundry documentation](https://learn.microsoft.com/azure/foundry/)
