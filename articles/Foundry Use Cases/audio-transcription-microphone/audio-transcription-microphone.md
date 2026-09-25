---
title: "Foundry use case: audio transcription from a microphone"
excerpt: "Capture live microphone audio with Python, transcribe it through a Microsoft Foundry realtime deployment, and save the transcript to a text file."
slug: foundry-use-cases/audio-transcription-microphone
articleId: f0ab89f5-1562-41f4-b1b5-2c9195372c54
artifactPath: "Foundry Use Cases/audio-transcription-microphone"
tags: ["Microsoft Foundry", "Azure AI", "Python", "audio transcription", "microphone", "realtime"]
series: {"slug":"foundry-use-cases","title":"Microsoft Foundry - Use Cases","part":8}
publishAt: "2026-10-02T12:52:00.000Z"
---
# Getting Started: Live Microphone Transcription with Microsoft Foundry

This use case is the live-microphone counterpart to [Audio Transcription from a WAV File](../7%20-%20audio-transcription-file/audio-transcription.md). Instead of reading a fixed file, the Python CLI captures speech from the microphone and streams it to a Microsoft Foundry realtime deployment. Each completed speech turn is printed to the terminal and saved to `output.txt`.

The application is transcription-only: it does not generate a spoken response. That makes it useful for live captions, dictation, voice commands, and applications that need text as soon as a speaker finishes a turn.

## What you will build

The script:

1. Authenticates with `DefaultAzureCredential`.
2. Connects to the `GPT-TRANSCRIBE` deployment over a Realtime WebSocket.
3. Captures 24 kHz mono PCM16 microphone chunks with `sounddevice`.
4. Streams chunks continuously to the Realtime API.
5. Uses server-side voice activity detection to detect completed turns.
6. Prints each transcription and saves the complete session to `output.txt`.

## Prerequisites

- A Microsoft Foundry project with a realtime transcription deployment named `GPT-TRANSCRIBE`, or the exact deployment name configured in `.env`.
- Azure credentials available to `DefaultAzureCredential`, such as an authenticated Azure CLI session.
- The `Cognitive Services OpenAI User` role, or equivalent permission.
- Python 3.10 or later.
- A working microphone.

## Project files

- [`transcribe_microphone.py`](code/transcribe_microphone.py) - runnable Python example
- [`.env.example`](code/.env.example) - configuration template
- [`requirements.txt`](code/requirements.txt) - Python dependencies
- [`README.md`](code/README.md) - quick local run notes

## Configuration

Copy `.env.example` to `.env` and set the project endpoint:

```dotenv
PROJECT_ENDPOINT=https://<resource-name>.services.ai.azure.com/api/projects/<project-name>
MODEL=GPT-TRANSCRIBE
OUTPUT_TXT=output.txt
```

`MODEL` must be the exact deployment name from the Foundry **Models + endpoints** page.

## Install and run

Run the sample from the article's `code` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python .\transcribe_microphone.py
```

Speak into the microphone. When you pause, server-side voice activity detection identifies the end of the turn and the completed transcript is printed. Press `Ctrl+C` to stop and write all captured turns to `output.txt`.

Expected output:

```text
Listening... speak into the microphone. Press Ctrl+C to stop.

Transcript: The customer asked for a consumption report.

Transcript: We should schedule a follow-up next week.

Stopped.
Saved transcript to C:\path\to\code\output.txt
```

## The microphone and realtime session

The microphone callback places 100 ms PCM16 chunks on a queue:

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

The sender task reads that queue and appends each chunk to the realtime input buffer:

```python
await connection.input_audio_buffer.append(
    audio=base64.b64encode(chunk).decode("ascii")
)
```

The session enables input transcription and server-side voice activity detection. When the service detects that the speaker has stopped, it emits `conversation.item.input_audio_transcription.completed`. The receiver task prints that event and adds it to the transcript list.

## Why `gpt-realtime` is a good fit

`gpt-realtime` is designed for audio that arrives continuously. The application does not need to wait for a complete recording before sending it; it can stream microphone chunks as they are captured. The persistent session, server-side turn detection, and event stream provide the low-latency behavior needed for live captions, dictation, and voice-controlled applications.

This is the live version of Article 7. Article 7 uses a WAV file but streams it at approximately playback speed. Article 8 replaces the file reader with a microphone callback while keeping the same core Realtime API pattern.

## Could `gpt-audio` be used instead?

Yes, but it would be a different architecture. `gpt-audio` is suitable when the application records a complete utterance first and then submits that WAV file as one Chat Completions request:

> **Complete recording -> one transcription response**

That approach can be simpler for voice memos, uploaded recordings, or push-to-talk applications where a user presses Stop before processing begins. It is less suitable for this always-listening example because the application would need to collect and segment each recording itself instead of streaming audio continuously and relying on server-side turn detection.

| Requirement | Recommended approach |
| --- | --- |
| Live microphone transcription | `gpt-realtime` |
| Captured utterance submitted after Stop | `gpt-audio` or a dedicated transcription endpoint |
| Live voice assistant with spoken replies | `gpt-realtime` |
| Long recordings, timestamps, or speaker diarization | Batch transcription service |

## WebSocket versus WebRTC

This Python CLI uses **WebSocket**. The connection is opened with `client.realtime.connect(model=MODEL)`, and microphone chunks plus transcription events travel over the same persistent, bidirectional connection. The `openai[realtime]` dependency installs the WebSocket support required by the Python client.

WebRTC is usually a better transport for a browser or mobile application because it integrates with microphone permissions and media devices. The model choice is independent of the transport: `gpt-realtime` is the session-oriented model, while WebSocket and WebRTC are connection options.

## Microsoft Learn resources

- [Use the GPT Realtime API via WebSockets](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/realtime-audio-websockets)
- [Audio capabilities in Azure OpenAI](https://learn.microsoft.com/azure/foundry-classic/openai/concepts/audio)
- [Microsoft Foundry documentation](https://learn.microsoft.com/azure/foundry/)
