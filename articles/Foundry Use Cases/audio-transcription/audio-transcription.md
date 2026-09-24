---
title: "Foundry use case: audio transcription"
excerpt: "Stream a WAV file to a Microsoft Foundry realtime transcription deployment, play the source audio, and save the resulting transcript to a text file."
slug: foundry-use-cases/audio-transcription
articleId: f7cd1216-31f0-4e43-9eeb-1688ba37dc88
artifactPath: "Foundry Use Cases/audio-transcription"
tags: ["Microsoft Foundry", "Azure AI", "Python", "audio transcription", "realtime"]
series: {"slug":"foundry-use-cases","title":"Microsoft Foundry - Use Cases","part":7}
publishAt: "2026-10-01T18:51:00.000Z"
---
# Getting Started: Audio Transcription with Microsoft Foundry

This use case transcribes a prerecorded WAV file with a Microsoft Foundry realtime deployment. The sample plays `input.wav` through the local speakers while it streams the same audio to the Realtime API. When the model finishes transcribing the audio, the transcript is printed to the terminal and saved to `output.txt`.

The example is intentionally built around a realtime session. The input file is sent in 100 ms chunks, which makes the sample behave like a live microphone source while remaining repeatable. This is useful when you are testing realtime transcription latency or preparing a later microphone integration.

## What you will build

The script:

1. Authenticates with `DefaultAzureCredential`.
2. Connects to the `GPT-TRANSCRIBE` deployment over a Realtime WebSocket.
3. Reads and validates a 24 kHz, mono, 16-bit PCM WAV file.
4. Plays the source audio locally while sending the same chunks to Foundry.
5. Receives the completed input-audio transcription.
6. Prints the transcript and saves it to `output.txt`.

This is a transcription-only flow: the model does not generate a spoken answer.

## Prerequisites

- A Microsoft Foundry project with a realtime transcription deployment named `GPT-TRANSCRIBE`, or the exact deployment name configured in `.env`.
- Azure credentials available to `DefaultAzureCredential`, such as an authenticated Azure CLI session.
- The `Cognitive Services OpenAI User` role, or equivalent permission.
- Python 3.10 or later.
- A working speaker.
- A WAV file in 24 kHz, mono, 16-bit PCM format.

## Project files

- [`transcribe_audio.py`](code/transcribe_audio.py) - runnable transcription example
- [`.env.example`](code/.env.example) - configuration template
- [`requirements.txt`](code/requirements.txt) - Python dependencies
- [`README.md`](code/README.md) - quick local run notes
- [`input.wav`](audio/input.wav) - sample input audio

## Configuration

Copy `.env.example` to `.env` and set the project endpoint:

```dotenv
PROJECT_ENDPOINT=https://<resource-name>.services.ai.azure.com/api/projects/<project-name>
MODEL=GPT-TRANSCRIBE
INPUT_WAV=../audio/input.wav
OUTPUT_TXT=output.txt
```

`MODEL` must be the exact deployment name from the Foundry **Models + endpoints** page. The sample uses `GPT-TRANSCRIBE` as the requested deployment name; deployment names are case-sensitive in some environments.

## Install and run

Run the sample from the article's `code` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python .\transcribe_audio.py
```

The sample plays the input audio, prints the transcript, and writes it to `code\output.txt`.

Expected output:

```text
Playing and transcribing input.wav with GPT-TRANSCRIBE...
Waiting for the transcription...

TRANSCRIPTION
-------------
We just achieved a major milestone ahead of schedule...

Saved transcription to C:\path\to\code\output.txt
```

## The realtime transcription session

The session requests text output and enables input-audio transcription:

```python
await connection.session.update(
    session={
        "type": "realtime",
        "output_modalities": ["text"],
        "audio": {
            "input": {
                "transcription": {"model": "whisper-1"},
                "format": {"type": "audio/pcm", "rate": 24000},
                "turn_detection": None,
            }
        },
    }
)
```

The application sends each chunk with `input_audio_buffer.append`, then explicitly calls `input_audio_buffer.commit` after the complete file has been sent. The completed transcript arrives in the `conversation.item.input_audio_transcription.completed` event.

## Why `gpt-realtime` is a good fit

`gpt-realtime` is a good fit when transcription is part of a low-latency audio pipeline. It accepts audio incrementally over a persistent session and emits the completed turn transcription through the same realtime event stream. The exact same pattern can later replace the WAV reader with a microphone callback, without changing the session or transcript handling.

This sample deliberately streams the file at approximately its playback rate. That allows you to observe the behavior of a live audio source while keeping the input deterministic. In a production microphone or voice application, the audio chunks would arrive from the device rather than from disk.

## Could `gpt-audio` be used instead?

Yes. `gpt-audio` could accept the complete WAV file in a Chat Completions request and return a text transcription. It can also return audio if the application requests a spoken response. That would be a reasonable choice for a **discrete file transcription** workflow:

> **Complete WAV file -> one transcription response**

For this article, however, `gpt-realtime` is the better fit because the goal is to demonstrate incremental delivery, realtime session events, and a path toward live microphone transcription. `gpt-audio` would be simpler if the complete recording is already available and low latency during capture is not important.

| Requirement | Recommended approach |
| --- | --- |
| Transcribe a complete recording after upload | `gpt-audio` or a dedicated transcription endpoint |
| Transcribe audio as it is captured | `gpt-realtime` |
| Build a live voice assistant with turn detection | `gpt-realtime` |
| Transcribe hours of recordings with diarization and timestamps | Batch transcription service |

For long recordings, meeting archives, or call-center data, a dedicated batch transcription service is usually more appropriate than either conversational model. Batch services are designed for throughput, long duration, timestamps, and speaker diarization.

## WebSocket versus WebRTC

This sample uses WebSocket because it is a Python CLI that explicitly controls the audio bytes and local playback. The connection is created with `client.realtime.connect(model=MODEL)`, and the application sends audio chunks and receives transcription events over that persistent connection.

WebRTC is usually a better transport for a browser or mobile application because it integrates naturally with media devices, permissions, and low-latency media transport. The model choice does not change: `gpt-realtime` is the session-oriented model, while WebSocket and WebRTC are two ways to connect to it.

## Microsoft Learn resources

- [Use the GPT Realtime API via WebSockets](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/realtime-audio-websockets)
- [Audio capabilities in Azure OpenAI](https://learn.microsoft.com/azure/foundry-classic/openai/concepts/audio)
- [Microsoft Foundry documentation](https://learn.microsoft.com/azure/foundry/)
