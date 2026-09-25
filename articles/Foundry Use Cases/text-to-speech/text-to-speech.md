---
title: "Text to Speech"
excerpt: "Turn written text into natural-sounding speech using Microsoft Foundry audio completions, Python, Entra ID authentication, and the OpenAI-compatible chat completions API with the audio modality."
slug: foundry-use-cases/text-to-speech
articleId: 78d1e3fc-952f-47d4-a933-7fe9e2232fdd
artifactPath: "Foundry Use Cases/text-to-speech"
tags: ["Microsoft Foundry", "Azure AI", "Python", "text to speech"]
series: {"slug":"foundry-use-cases","title":"Microsoft Foundry - Use Cases","part":5}
publishAt: "2026-10-02T17:53:00.000Z"
---
# Discrete audio responses with Microsoft Foundry audio completions

This use case is about a **discrete audio request**: submit a complete piece of text or a recorded WAV request, wait for the model to finish, and save one spoken MP3 response. It is not a live conversation. Microsoft Foundry audio-enabled models can turn written text into natural-sounding speech, or listen to a recorded request and speak an answer.

The sample is based on the GPT Audio implementation used by the larger Foundry Chat App. By default, it keeps the text-to-speech instruction separate from the text being read: the model is asked to speak the input verbatim rather than answer or summarize it. An optional audio mode accepts a WAV question, generates an answer, and returns that answer as spoken audio.

## What you will build

The script:

1. Authenticates with `DefaultAzureCredential`.
2. Derives the project OpenAI endpoint from `PROJECT_ENDPOINT`.
3. Reads text from `prompt.txt` (or `TEXT` in `.env`), or reads a WAV request when `INPUT_MODE=audio`.
4. Sends text or audio with `modalities=["text", "audio"]`.
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
INPUT_MODE=text
INPUT_AUDIO_FILE=input.wav
OUTPUT_FILE=speech
```

By default, the script reads the text to speak from `prompt.txt`. Edit that file to change what's read aloud, or set `TEXT` in `.env` to override it — `TEXT` takes precedence over `TEXT_FILE` when both are set.

Set `INPUT_MODE=audio` to switch to audio-in/audio-out mode. In that mode, `INPUT_AUDIO_FILE` must point to a WAV file containing the user's spoken request. The model listens to the request, generates an answer, and returns the answer as an MP3. The optional instruction in the request can be adjusted in `text_to_speech.py` if you want a different response style.

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

## Two input modes

This example supports two discrete audio completion patterns:

| Mode | Input | Model behavior | Output |
| --- | --- | --- | --- |
| `text` (default) | Text from `TEXT` or `prompt.txt` | Reads the supplied text verbatim | Spoken MP3 |
| `audio` | A WAV file from `INPUT_AUDIO_FILE` | Understands the request and generates an answer | Spoken MP3 |

To try audio-in/audio-out mode:

```dotenv
INPUT_MODE=audio
INPUT_AUDIO_FILE=input.wav
```

The WAV file is base64-encoded and sent as an `input_audio` message part. This is a single Chat Completions request, not a live stream: the complete input file is submitted, and the spoken answer is returned after the model has processed it.

The relevant request shape is:

```python
{
    "role": "user",
    "content": [
        {
            "type": "text",
            "text": "Listen to the attached WAV request and answer it aloud.",
        },
        {
            "type": "input_audio",
            "input_audio": {
                "data": encoded_wav,
                "format": "wav",
            },
        },
    ],
}
```

## Why `gpt-audio` is the right model family here

The audio completion model used here is designed for a complete request/response exchange through the Chat Completions API. It can accept text or a complete audio file, generate text and audio, and return the spoken result in one response. That matches both modes in this article:

- **Text mode:** prepared text -> spoken audio.
- **Audio mode:** recorded WAV request -> model-generated spoken answer.

The complete input is submitted before processing, and the response is returned after the model has generated it. There is no need for a persistent session, incremental audio buffering, server-side voice activity detection, or interruption handling. If the requirement is only reliable, controllable speech synthesis, a dedicated TTS endpoint may be simpler still.

## Why not use `gpt-realtime` here?

`gpt-realtime` is designed for an ongoing voice conversation: audio is streamed in and out over a persistent Realtime API session, with turn detection and interruptions. Those capabilities are valuable when a user is actively talking with the application, but they add transport and session complexity to this one-shot workflow.

Use `gpt-realtime` for live microphone or telephony conversations. Use the audio completion model for a complete text or WAV request that should produce one spoken result.

## Choosing a voice and format

Audio completions support voices including `alloy`, `ash`, `ballad`, `coral`, `echo`, `sage`, `shimmer`, `verse`, `marin`, and `cedar`, subject to the deployed model and API version. The example uses `alloy`. MP3 is convenient for a small downloadable file; the service also supports formats such as WAV, FLAC, OPUS, PCM16, and AAC.

## Microsoft Learn resources

- [Quickstart: Get started with Azure OpenAI audio generation](https://learn.microsoft.com/azure/foundry/openai/audio-completions-quickstart)
- [Audio capabilities in Azure OpenAI](https://learn.microsoft.com/azure/foundry-classic/openai/concepts/audio)
- [Microsoft Foundry documentation](https://learn.microsoft.com/azure/foundry/)
