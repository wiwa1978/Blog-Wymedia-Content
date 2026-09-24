---
title: "Foundry use case: realtime voice from a microphone"
excerpt: "Build a command-line voice assistant that captures microphone audio and plays responses from a Microsoft Foundry realtime GPT deployment."
slug: foundry-use-cases/realtime-voice-microphone
articleId: 2e51c9f4-2ef1-45bd-9de1-379d517ef4a2
artifactPath: "Foundry Use Cases/realtime-voice-microphone"
tags: ["Microsoft Foundry", "Azure AI", "Python", "realtime voice", "microphone"]
series: {"slug":"foundry-use-cases","title":"Microsoft Foundry - Use Cases","part":6}
publishAt: "2026-09-30T18:30:00.000Z"
---
# Getting Started: Live Microphone Voice with Microsoft Foundry

This use case is a **live, interactive voice assistant**. The Microsoft Foundry realtime GPT model listens to a microphone, detects spoken turns, and speaks back with low latency. The Python CLI captures microphone audio, streams PCM chunks over a Realtime WebSocket connection, receives the assistant's audio, and plays it through the default speakers.

This is different from the companion `5 - realtime-voice-mp3` use case, which sends a prerecorded WAV file. Both samples use the same realtime GPT model; only the audio source and playback experience differ.

## What you will build

The script:

1. Authenticates with `DefaultAzureCredential`.
2. Connects to a realtime GPT deployment using `PROJECT_ENDPOINT`.
3. Captures microphone audio with `sounddevice`.
4. Streams 24 kHz mono PCM16 chunks to Foundry.
5. Detects the end of each spoken turn with server-side VAD.
6. Plays the assistant's PCM audio through the default speakers.

## Prerequisites

- A Microsoft Foundry project with a realtime GPT deployment, such as `gpt-realtime`.
- The exact deployment name from **Models + endpoints**.
- Azure credentials available to `DefaultAzureCredential`, such as an authenticated Azure CLI session.
- The `Cognitive Services OpenAI User` role, or equivalent permission.
- Python 3.10 or later.
- A working microphone and speaker.

## Project files

- [`realtime_microphone.py`](code/realtime_microphone.py) - runnable CLI example
- [`.env.example`](code/.env.example) - configuration template
- [`requirements.txt`](code/requirements.txt) - Python dependencies
- [`README.md`](code/README.md) - quick local run notes

## Configuration

Copy `.env.example` to `.env` and set the project endpoint and deployment:

```dotenv
PROJECT_ENDPOINT=https://<resource-name>.services.ai.azure.com/api/projects/<project-name>
MODEL=gpt-realtime
VOICE=alloy
INSTRUCTIONS=You are a helpful Microsoft Foundry voice assistant. Keep responses concise and conversational.
```

`PROJECT_ENDPOINT` is the project endpoint shown in Foundry. The script derives the project-scoped OpenAI WebSocket base URL from it.

## Install and run

Run the sample from the article's `code` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`, then start the assistant:

```powershell
python .\realtime_microphone.py
```

Speak into the microphone. The terminal prints transcripts while the assistant's response plays through the default speakers. Press `Ctrl+C` to stop.

## Capturing microphone audio

The script requests 24 kHz, mono, 16-bit PCM audio:

```python
with sd.RawInputStream(
    samplerate=24_000,
    blocksize=2_400,
    channels=1,
    dtype="int16",
    callback=on_audio,
):
    ...
```

The callback places each 100 ms audio block on a queue. The async sender reads that queue and base64-encodes each block for `input_audio_buffer.append`.

## Reading and playing the response

Assistant audio arrives as base64-encoded PCM16 deltas. The CLI decodes each delta and writes it to a `sounddevice.RawOutputStream`:

```python
audio = base64.b64decode(event.delta)
output_stream.write(audio)
```

The same event stream also contains the user's completed transcript and the assistant's spoken transcript deltas.

## Live turn detection

Server-side voice activity detection lets the service recognize when the user has stopped speaking and automatically create a response:

```python
"turn_detection": {
    "type": "server_vad",
    "silence_duration_ms": 500,
    "create_response": True,
}
```

The microphone task and response task run concurrently. This is what makes the CLI interactive rather than a file upload followed by a delayed response.

## Why `gpt-realtime` is the right model family here

This application needs a persistent session so it can send microphone audio continuously, detect when the user has stopped speaking, begin a response quickly, and support interruption while the assistant is speaking. `gpt-realtime` provides that interaction model through the Realtime API.

## Why not use `gpt-audio` here?

`gpt-audio` is a good choice for a complete recorded request followed by one spoken answer. It is not the best fit for this live microphone flow because the application would need to collect and submit discrete requests rather than continuously stream microphone audio.

Using `gpt-audio` would also mean managing more of the turn lifecycle and conversation state in the application. `gpt-realtime` fits better because it is designed for persistent sessions, natural turn-taking, server-side voice activity detection, interruption, and live audio input and output.

## WebSocket versus WebRTC

This sample uses the Realtime API over **WebSocket**. WebSocket is a persistent, bidirectional connection: the client sends microphone audio and session events, while the service sends transcripts, response events, and audio deltas back over the same connection. It works well for this Python command-line sample because the application reads and plays audio through the operating system's devices directly.

The connection is created in `realtime_microphone.py` by configuring the project-scoped `wss://` endpoint and then calling:

```python
client = AsyncOpenAI(
    websocket_base_url=websocket_base_url(PROJECT_ENDPOINT),
    api_key=token_provider(),
)

async with client.realtime.connect(model=MODEL) as connection:
    ...
```

The `websocket_base_url` helper converts the HTTPS project endpoint into the WebSocket endpoint. `send_microphone_audio` sends microphone chunks with `connection.input_audio_buffer.append(...)`, while `receive_assistant_audio` listens with `async for event in connection` and plays the returned audio deltas.

**WebRTC** is another transport supported by the Realtime API. It is usually the better choice for a browser or mobile application because it is designed for low-latency media transport and integrates naturally with microphones, speakers, permissions, and network conditions. WebSocket is more convenient for a CLI, test harness, backend service, or automation workflow where the application wants explicit control over the audio bytes.

The Foundry Playground uses browser microphone capture with WebRTC. This article uses WebSocket because it is a Python CLI and accesses the microphone and speakers directly through `sounddevice`.
