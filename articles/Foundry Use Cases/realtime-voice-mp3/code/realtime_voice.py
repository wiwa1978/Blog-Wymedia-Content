"""Stream speech to a Microsoft Foundry realtime GPT model and save the reply."""

import asyncio
import base64
import os
import wave
from pathlib import Path

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AsyncOpenAI


SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")

SAMPLE_RATE = 24_000
CHANNELS = 1
SAMPLE_WIDTH_BYTES = 2
CHUNK_SIZE_BYTES = 4_800  # 100 ms of 24 kHz, mono, 16-bit PCM audio.


def required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("<"):
        raise ValueError(f"Set {name} in .env before running this script.")
    return value


PROJECT_ENDPOINT = required_setting("PROJECT_ENDPOINT")
MODEL = required_setting("MODEL")
VOICE = os.getenv("VOICE", "alloy").strip() or "alloy"
INPUT_WAV = SCRIPT_DIR / (os.getenv("INPUT_WAV", "input.wav").strip() or "input.wav")
OUTPUT_WAV = SCRIPT_DIR / (os.getenv("OUTPUT_WAV", "output.wav").strip() or "output.wav")
OUTPUT_TXT = SCRIPT_DIR / (os.getenv("OUTPUT_TXT", "output.txt").strip() or "output.txt")
INSTRUCTIONS = os.getenv(
    "INSTRUCTIONS",
    "You are a helpful voice assistant. Keep responses concise and conversational.",
).strip()


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
        raise FileNotFoundError(
            f"Create {path.name} first. It must be 24 kHz, mono, 16-bit PCM WAV audio."
        )

    with wave.open(str(path), "rb") as wav_file:
        if wav_file.getframerate() != SAMPLE_RATE:
            raise ValueError(f"{path.name} must use a {SAMPLE_RATE} Hz sample rate.")
        if wav_file.getnchannels() != CHANNELS:
            raise ValueError(f"{path.name} must be mono.")
        if wav_file.getsampwidth() != SAMPLE_WIDTH_BYTES:
            raise ValueError(f"{path.name} must be 16-bit PCM.")
        return wav_file.readframes(wav_file.getnframes())


def write_pcm_to_wav(path: Path, pcm_audio: bytes) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(SAMPLE_WIDTH_BYTES)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm_audio)


async def main() -> None:
    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(
        credential,
        "https://ai.azure.com/.default",
    )
    client = AsyncOpenAI(
        websocket_base_url=websocket_base_url(PROJECT_ENDPOINT),
        api_key=token_provider(),
    )

    input_pcm = read_pcm_from_wav(INPUT_WAV)
    input_pcm += b"\x00" * CHUNK_SIZE_BYTES * 10
    output_pcm = bytearray()
    input_transcript = ""
    response_transcript = ""

    try:
        async with client.realtime.connect(model=MODEL) as connection:
            await connection.session.update(
                session={
                    "type": "realtime",
                    "instructions": INSTRUCTIONS,
                    "output_modalities": ["audio"],
                    "audio": {
                        "input": {
                            "transcription": {"model": "whisper-1"},
                            "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                            "turn_detection": {
                                "type": "server_vad",
                                "threshold": 0.5,
                                "prefix_padding_ms": 300,
                                "silence_duration_ms": 500,
                                "create_response": True,
                                "interrupt_response": False,
                            },
                        },
                        "output": {
                            "voice": VOICE,
                            "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                        },
                    },
                }
            )

            print(f"Streaming {INPUT_WAV.name} to {MODEL}...")
            for offset in range(0, len(input_pcm), CHUNK_SIZE_BYTES):
                chunk = input_pcm[offset : offset + CHUNK_SIZE_BYTES]
                await connection.input_audio_buffer.append(
                    audio=base64.b64encode(chunk).decode("ascii")
                )
                await asyncio.sleep(0.1)

            print("Waiting for the realtime response...")
            response_started = False
            async for event in connection:
                if event.type == "conversation.item.input_audio_transcription.completed":
                    input_transcript = event.transcript
                    print("\n" + "-" * 20)
                    print("YOU SAID")
                    print("-" * 20)
                    print(event.transcript)
                elif event.type == "response.output_audio_transcript.delta":
                    if not response_started:
                        print("\n" + "-" * 20)
                        print("MODEL RESPONSE")
                        print("-" * 20)
                        response_started = True
                    response_transcript += event.delta
                    print(event.delta, end="", flush=True)
                elif event.type == "response.output_audio.delta":
                    output_pcm.extend(base64.b64decode(event.delta))
                elif event.type == "error":
                    raise RuntimeError(f"Realtime API error: {event.error.message}")
                elif event.type == "response.done":
                    break
    finally:
        await client.close()
        credential.close()

    if not output_pcm:
        raise RuntimeError("The realtime model did not return audio.")

    write_pcm_to_wav(OUTPUT_WAV, bytes(output_pcm))
    print(f"\nSaved spoken reply to {OUTPUT_WAV}")

    OUTPUT_TXT.write_text(
        f"YOU SAID:\n{input_transcript}\n\nMODEL RESPONSE:\n{response_transcript}\n",
        encoding="utf-8",
    )
    print(f"Saved transcript to {OUTPUT_TXT}")


if __name__ == "__main__":
    asyncio.run(main())
