"""Stream a WAV file to Microsoft Foundry and save its transcription."""

import asyncio
import base64
import os
import wave
from pathlib import Path

import sounddevice as sd
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AsyncOpenAI


SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")

SAMPLE_RATE = 24_000
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2
CHUNK_SIZE_BYTES = 4_800


def required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("<"):
        raise ValueError(f"Set {name} in .env before running this script.")
    return value


PROJECT_ENDPOINT = required_setting("PROJECT_ENDPOINT")
MODEL = required_setting("MODEL")
INPUT_WAV = (SCRIPT_DIR / os.getenv("INPUT_WAV", "../audio/input.wav")).resolve()
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


def read_pcm_from_wav(path: Path) -> bytes:
    if not path.exists():
        raise FileNotFoundError(f"Create {path} before running this script.")

    with wave.open(str(path), "rb") as wav_file:
        if wav_file.getframerate() != SAMPLE_RATE:
            raise ValueError(f"{path.name} must use a {SAMPLE_RATE} Hz sample rate.")
        if wav_file.getnchannels() != CHANNELS:
            raise ValueError(f"{path.name} must be mono.")
        if wav_file.getsampwidth() != SAMPLE_WIDTH_BYTES:
            raise ValueError(f"{path.name} must be 16-bit PCM.")
        return wav_file.readframes(wav_file.getnframes())


async def main() -> None:
    input_pcm = read_pcm_from_wav(INPUT_WAV)
    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(
        credential,
        "https://ai.azure.com/.default",
    )
    client = AsyncOpenAI(
        websocket_base_url=websocket_base_url(PROJECT_ENDPOINT),
        api_key=token_provider(),
    )
    transcript = ""

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
                            "turn_detection": None,
                        }
                    },
                }
            )

            print(f"Playing and transcribing {INPUT_WAV.name} with {MODEL}...")
            with sd.RawOutputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
            ) as output_stream:
                for offset in range(0, len(input_pcm), CHUNK_SIZE_BYTES):
                    chunk = input_pcm[offset : offset + CHUNK_SIZE_BYTES]
                    output_stream.write(chunk)
                    await connection.input_audio_buffer.append(
                        audio=base64.b64encode(chunk).decode("ascii")
                    )
                    await asyncio.sleep(0.1)

            await connection.input_audio_buffer.commit()
            print("Waiting for the transcription...")

            async for event in connection:
                if event.type == "conversation.item.input_audio_transcription.completed":
                    transcript = event.transcript
                    break
                if event.type == "error":
                    raise RuntimeError(f"Realtime API error: {event.error.message}")
    finally:
        await client.close()
        credential.close()

    if not transcript:
        raise RuntimeError("The realtime model did not return a transcription.")

    print("\nTRANSCRIPTION")
    print("-------------")
    print(transcript)
    OUTPUT_TXT.write_text(transcript + "\n", encoding="utf-8")
    print(f"\nSaved transcription to {OUTPUT_TXT}")


if __name__ == "__main__":
    asyncio.run(main())
