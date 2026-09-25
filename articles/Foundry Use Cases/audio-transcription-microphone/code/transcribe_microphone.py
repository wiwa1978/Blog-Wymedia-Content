"""Transcribe live microphone audio with Microsoft Foundry realtime GPT."""

import asyncio
import base64
import os
import queue
from pathlib import Path

import sounddevice as sd
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AsyncOpenAI


SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")

SAMPLE_RATE = 24_000
CHANNELS = 1
CHUNK_FRAMES = 2_400


def required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("<"):
        raise ValueError(f"Set {name} in .env before running this script.")
    return value


PROJECT_ENDPOINT = required_setting("PROJECT_ENDPOINT")
MODEL = required_setting("MODEL")
OUTPUT_TXT = (SCRIPT_DIR / os.getenv("OUTPUT_TXT", "output.txt")).resolve()


def websocket_base_url(project_endpoint: str) -> str:
    project_endpoint = project_endpoint.strip().rstrip("/")
    if not project_endpoint.startswith("https://"):
        raise ValueError("PROJECT_ENDPOINT must be an HTTPS endpoint.")

    websocket_endpoint = project_endpoint.replace("https://", "wss://", 1)
    if websocket_endpoint.endswith("/openai/v1"):
        return websocket_endpoint
    if "/api/projects/" in websocket_endpoint:
        host = websocket_endpoint.split("/api/projects/", 1)[0]
        return f"{host}/openai/v1"
    if websocket_endpoint.endswith("/openai"):
        return f"{websocket_endpoint}/v1"
    return f"{websocket_endpoint}/openai/v1"


async def send_microphone_audio(connection, audio_queue: queue.Queue[bytes]) -> None:
    while True:
        chunk = await asyncio.to_thread(audio_queue.get)
        await connection.input_audio_buffer.append(
            audio=base64.b64encode(chunk).decode("ascii")
        )


async def receive_transcripts(connection, transcripts: list[str]) -> None:
    async for event in connection:
        if event.type == "conversation.item.input_audio_transcription.completed":
            transcripts.append(event.transcript)
            print(f"\nTranscript: {event.transcript}", flush=True)
        elif event.type == "error":
            raise RuntimeError(f"Realtime API error: {event.error.message}")


async def main() -> None:
    audio_queue: queue.Queue[bytes] = queue.Queue(maxsize=20)
    transcripts: list[str] = []

    def on_audio(indata, frames, time_info, status) -> None:
        if status:
            print(f"\nMicrophone: {status}", flush=True)
        try:
            audio_queue.put_nowait(bytes(indata))
        except queue.Full:
            print("\nAudio queue is full; dropping a microphone chunk.", flush=True)

    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(
        credential,
        "https://ai.azure.com/.default",
    )
    client = AsyncOpenAI(
        websocket_base_url=websocket_base_url(PROJECT_ENDPOINT),
        api_key=token_provider(),
    )

    try:
        async with client.realtime.connect(model=MODEL) as connection:
            await connection.session.update(
                session={
                    "type": "realtime",
                    "output_modalities": ["text"],
                    "audio": {
                        "input": {
                            "transcription": {"model": "whisper-1"},
                            "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                            "turn_detection": {
                                "type": "server_vad",
                                "threshold": 0.5,
                                "prefix_padding_ms": 300,
                                "silence_duration_ms": 700,
                                "create_response": False,
                            },
                        }
                    },
                }
            )

            print("Listening... speak into the microphone. Press Ctrl+C to stop.")
            with sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=CHUNK_FRAMES,
                channels=CHANNELS,
                dtype="int16",
                callback=on_audio,
            ):
                await asyncio.gather(
                    send_microphone_audio(connection, audio_queue),
                    receive_transcripts(connection, transcripts),
                )
    finally:
        await client.close()
        credential.close()
        OUTPUT_TXT.write_text("\n".join(transcripts) + "\n", encoding="utf-8")
        print(f"\nSaved transcript to {OUTPUT_TXT}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
