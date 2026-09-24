---
title: "Foundry use case: realtime voice from a WAV file"
excerpt: "Send a prerecorded WAV file to a Microsoft Foundry realtime GPT deployment and save the spoken response as audio."
slug: foundry-use-cases/realtime-voice-mp3
articleId: bb6b5fb7-2673-4e18-8090-8bbef33bc344
artifactPath: "Foundry Use Cases/realtime-voice-mp3"
tags: ["Microsoft Foundry", "Azure AI", "Python", "realtime voice", "audio"]
series: {"slug":"foundry-use-cases","title":"Microsoft Foundry - Use Cases","part":5}
publishAt: "2026-09-29T18:29:00.000Z"
---
# Getting Started: Testing Realtime Voice from a WAV File with Microsoft Foundry

This use case demonstrates a **realtime voice conversation without requiring a microphone**. A prerecorded WAV file stands in for a user's live speech, but the file is sent in small chunks over time. The model listens, detects the end of the turn, reasons, and streams a spoken response over one live connection.

This makes the sample repeatable while still exercising the parts that matter in a realtime system: incremental audio delivery, server-side voice activity detection, response latency, event handling, and streamed audio output. It is not simply a file-to-file conversion example.

Concretely, the script prints two things to the console as they arrive: the transcript of what was "said" in the input file, and the transcript of the model's spoken reply. Both transcripts are also written to `output.txt` so you have a permanent record without needing to copy them from the terminal. The model's actual spoken reply — the audio itself, not just its transcript — is saved as a new file, `output.wav`, which you can play back in any audio player.

## What you will build

The script:

1. Authenticates with `DefaultAzureCredential`.
2. Connects to a realtime GPT deployment with the OpenAI Python realtime client.
3. Configures a speech-in, speech-out session with a voice and server-side VAD.
4. Streams 24 kHz mono PCM audio chunks to the model.
5. Prints the model's transcript deltas as they arrive.
6. Saves the model's audio reply as `output.wav`.
7. Saves both transcripts (what you said and the model's reply) as `output.txt`.

## Prerequisites

- A Microsoft Foundry project with a realtime GPT deployment, such as `gpt-realtime`.
- The exact realtime deployment name from **Models + endpoints**. The deployment name can differ from the base model name.
- Azure credentials available to `DefaultAzureCredential`, for example an authenticated Azure CLI session.
- The `Cognitive Services OpenAI User` role, or equivalent permission to call the deployment.
- Python 3.10 or later.
- A short WAV file recorded as 24 kHz, mono, 16-bit PCM audio. If you only have an MP3, convert it first with FFmpeg (see below).

Realtime models are used from the Foundry **Audio** playground or Realtime API. The normal chat playground is not the right surface for these deployments.

## Project files

- [`realtime_voice.py`](code/realtime_voice.py) - runnable Python example
- [`.env.example`](code/.env.example) - configuration template
- [`requirements.txt`](code/requirements.txt) - Python dependencies
- [`README.md`](code/README.md) - quick local run notes

Clicking the code link opens the source in the site's code modal; it can also be downloaded from there.

## Configuration

Copy `.env.example` to `.env` and set the endpoint and deployment:

```dotenv
PROJECT_ENDPOINT=https://<resource-name>.services.ai.azure.com/api/projects/<project-name>
MODEL=gpt-realtime
VOICE=alloy
INPUT_WAV=input.wav
OUTPUT_WAV=output.wav
OUTPUT_TXT=output.txt
INSTRUCTIONS=You are a helpful Microsoft Foundry voice assistant. Keep responses concise and conversational.
```

`PROJECT_ENDPOINT` is the project endpoint shown in Foundry. The sample derives the project-scoped OpenAI WebSocket base URL from it.

## Install and run

Run the sample from the article's `code` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`, set `INPUT_WAV` to your WAV file, then run:

```powershell
python .\realtime_voice.py
```

If you only have an MP3 file, convert it to WAV first with FFmpeg:

```powershell
ffmpeg -i input.mp3 -ar 24000 -ac 1 -sample_fmt s16 input.wav
```

This produces a WAV file at the exact 24 kHz, mono, 16-bit PCM format the sample expects.

Expected terminal output looks like this:

```text
Streaming input.wav to gpt-realtime...
Waiting for the realtime response...

--------------------
YOU SAID
--------------------
We just achieved a major milestone ahead of schedule. The team worked incredibly hard, and the results exceeded our expectations. I'm excited to share what this means for our customers and partners.

--------------------
MODEL RESPONSE
--------------------
That's fantastic news! Achieving a major milestone ahead of schedule is a testament to the team's dedication and hard work. It's going to have a big impact on your customers and partners, bringing them even more value sooner than expected. How would you like to share this news with them—through a special announcement, or maybe a detailed update on the benefits they can look forward to?
Saved spoken reply to C:\path\to\code\output.wav
Saved transcript to C:\path\to\code\output.txt
```

Open `output.wav` in any audio player. Here are the actual input and output files from this run:

**Input (`input.wav`)**

<audio controls src="audio/input.wav"></audio>

**Model's spoken reply (`output.wav`)**

<audio controls src="audio/output.wav"></audio>

## The core realtime session

The most important part is the `session.update` call. It tells the realtime model that this is a speech-in, speech-out session, configures transcription for user audio, chooses a response voice, and enables server-side voice activity detection.

```python
await connection.session.update(
    session={
        "type": "realtime",
        "instructions": INSTRUCTIONS,
        "output_modalities": ["audio"],
        "audio": {
            "input": {
                "transcription": {"model": "whisper-1"},
                "format": {"type": "audio/pcm", "rate": 24000},
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                    "create_response": True,
                },
            },
            "output": {
                "voice": VOICE,
                "format": {"type": "audio/pcm", "rate": 24000},
            },
        },
    }
)
```

With `create_response` enabled, the service can detect the end of the user's turn and begin the model response automatically.

## Streaming audio in

The Realtime API expects PCM audio chunks as base64. The sample reads a WAV file, validates that it is 24 kHz mono 16-bit PCM, then sends 100 ms chunks.

```python
for offset in range(0, len(input_pcm), CHUNK_SIZE_BYTES):
    chunk = input_pcm[offset : offset + CHUNK_SIZE_BYTES]
    await connection.input_audio_buffer.append(
        audio=base64.b64encode(chunk).decode("ascii")
    )
    await asyncio.sleep(0.1)
```

The short sleep is intentional: it simulates real-time audio streaming instead of uploading the whole file as fast as possible.

## Reading the spoken reply

The model sends structured events back over the same connection:

| Event | Meaning |
| --- | --- |
| `conversation.item.input_audio_transcription.completed` | Final transcript of what the user said |
| `response.output_audio_transcript.delta` | Text transcript of the assistant's spoken reply |
| `response.output_audio.delta` | Base64 PCM audio for the assistant's voice |
| `response.done` | The response is complete |
| `error` | The realtime session reported an error |

The script collects `response.output_audio.delta` chunks and wraps them in a WAV file at the end.

## Transcribing the conversation

`output.txt` is not just script logging — it is the actual speech-to-text transcription of the audio, produced by the Realtime API itself. The Realtime API transcribes both sides of the conversation as text, in real time, over the same connection:

- **`YOU SAID`** is a genuine ASR (automatic speech recognition) transcription of `input.wav`, produced by a dedicated speech-to-text model (`whisper-1`), configured in `session.update` under `audio.input.transcription`. Once the service detects the end of your turn, it emits one `conversation.item.input_audio_transcription.completed` event containing the full transcript of what is actually in the audio file — not a copy of any text you typed, since the input here is audio only.
- **`MODEL RESPONSE`** is the text the realtime model is speaking, streamed via `response.output_audio_transcript.delta` events. These text chunks arrive alongside (not after) the `response.output_audio.delta` audio chunks that make up `output.wav` — the model generates its spoken words and its transcript together, so this text is an accurate transcript of what you hear in the reply audio.

In short: both halves of `output.txt` are transcriptions of audio — one of your input file, one of the model's spoken reply — not arbitrary print statements.

The script accumulates both transcripts as they stream in, then writes them to `output.txt` once the response is complete:

```python
OUTPUT_TXT.write_text(
    f"YOU SAID:\n{input_transcript}\n\nMODEL RESPONSE:\n{response_transcript}\n",
    encoding="utf-8",
)
```

This gives you a durable, text-searchable transcription of the conversation alongside the audio files — useful for reviewing runs later, feeding the transcript into another process, or verifying what the model actually heard versus what was in the source audio.

## From a file to a live microphone

Streaming a file is a good way to learn the model, session, and event flow without needing a microphone. The same Realtime API works with live audio too — see the companion use case `6 - realtime-voice-microphone`, which replaces the file with live microphone capture and speaker playback for a real interactive voice assistant.

## Real-world use cases

This pattern's real value is producing a *spoken* reply, not just a transcript — so it fits scenarios where hearing the model's response actually matters:

- **Voice bot / IVR regression testing.** Keep a library of prerecorded customer utterances (as WAV files) and replay them through the same session your live voice bot uses. Because the reply comes back as audio, you can catch regressions in the bot's actual voice output — pronunciation, tone, latency — not just its intent-detection logic. A text-only check would miss those.
- **Language learning feedback.** Have a learner record a phrase, stream it through, and return a spoken correction or conversational follow-up. The learner needs to *hear* the corrected pronunciation, not just read it, so the audio reply is the point.
- **Hands-free voice assistants.** Scenarios where the user can't look at a screen (driving, cooking, accessibility needs) — record a short voice request, get back a spoken answer. The transcript in `output.txt` is a helpful side effect, but the audio reply is what the user actually consumes.

If the task is really "get accurate text from audio" — voicemail triage, meeting notes, dictation, call archives — you don't need a spoken reply at all, so a plain batch transcription call is simpler and cheaper than this bidirectional pattern; see the note below.

For pure long-form transcription use cases like podcast episodes, meeting recordings, or call archives — where no spoken reply is needed and you just want accurate text — it's better to use a dedicated batch transcription service instead of this realtime, conversational pattern: the Azure OpenAI `/audio/transcriptions` endpoint (`whisper-1` or `gpt-4o-transcribe`), or the Azure AI Speech batch transcription API for hours-long audio with speaker diarization and timestamps. The Realtime API here is optimized for low-latency, turn-based conversation, not for efficiently transcribing bulk long-form audio.

## Why `gpt-audio` is not the best fit for this use case

`gpt-audio` accepts audio and returns audio through a conventional Chat Completions request. That is a good fit when a complete WAV request can be uploaded and processed as one discrete turn. This sample has a different goal: it deliberately models an ongoing, interruptible voice conversation.

Sending the whole WAV file to `gpt-audio` would produce a spoken answer, but it would not exercise incremental input, server-side turn detection, or the realtime event stream. `gpt-realtime` is recommended here because the use case is testing the same streaming behavior that a live voice assistant would use.

| Requirement | Why `gpt-audio` is less suitable | Why `gpt-realtime` fits better |
| --- | --- | --- |
| Continuous conversation | Uses request/response calls through Chat Completions | Designed for persistent live sessions |
| Natural interruptions | Requires more application-side orchestration | Built for realtime turn-taking and interruption |
| Low-latency voice interaction | Streaming helps, but the application still manages requests | Native realtime audio interaction |
| Session state | Managed primarily by the application | Maintained within the realtime session |

## WebSocket versus WebRTC

This sample uses the Realtime API over **WebSocket**. WebSocket is a persistent, bidirectional connection: the client sends audio and session events, while the service sends transcripts, response events, and audio deltas back over the same connection. It is a good fit for this Python command-line sample because the code controls the WAV file directly and does not need browser media handling.

The connection is created in `realtime_voice.py` by configuring the project-scoped `wss://` endpoint and then calling:

```python
client = AsyncOpenAI(
    websocket_base_url=websocket_base_url(PROJECT_ENDPOINT),
    api_key=token_provider(),
)

async with client.realtime.connect(model=MODEL) as connection:
    ...
```

The `websocket_base_url` helper converts the HTTPS project endpoint into the WebSocket endpoint. The `connection.input_audio_buffer.append(...)` calls send the WAV chunks, and `async for event in connection` receives the model's events.

**WebRTC** is another transport supported by the Realtime API. It is usually the better choice for a browser or mobile application because it is designed for low-latency media transport and integrates naturally with microphones, speakers, permissions, and network conditions. WebSocket is more convenient for a CLI, test harness, backend service, or automation workflow where the application wants explicit control over the audio bytes.

The Foundry Playground uses browser microphone capture with WebRTC. This article uses WebSocket because it is a Python CLI and streams a local file rather than attaching a browser media device.

## What to try next

1. Move to the companion `6 - realtime-voice-microphone` use case for live microphone input and speaker playback.
2. Add a loop so each audio file becomes one conversational turn.
3. Append each turn's transcripts to `output.txt` instead of overwriting it, to build a running conversation log.
4. Try different voices such as `alloy`, `verse`, or `shimmer`, depending on what your deployment supports.
5. Experiment with different chunk sizes and streaming delays to see how they affect turn detection timing.

## Microsoft Learn resources

- [Use the GPT Realtime API via WebSockets](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/realtime-audio-websockets)
- [Microsoft Foundry documentation](https://learn.microsoft.com/azure/foundry/)
- [Azure AI services authentication](https://learn.microsoft.com/azure/ai-services/authentication)
