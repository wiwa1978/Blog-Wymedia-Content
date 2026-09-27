"""Transcribe the default microphone with Azure Speech in Foundry Tools."""

import os
import re
import threading
from pathlib import Path
from urllib.parse import urlsplit

import azure.cognitiveservices.speech as speechsdk
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(SCRIPT_DIR / ".env")


def required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("<"):
        raise ValueError(f"Set {name} in {SCRIPT_DIR / '.env'} before running.")
    return value


def speech_endpoint() -> str:
    endpoint = required_setting("PROJECT_ENDPOINT").rstrip("/")
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
        or parsed.port
    ):
        raise ValueError(
            "PROJECT_ENDPOINT must be an HTTPS Foundry project or Speech resource URL."
        )
    if parsed.hostname.endswith(".cognitiveservices.azure.com") and not parsed.path:
        return endpoint
    if parsed.hostname.endswith(".services.ai.azure.com") and re.fullmatch(
        r"/api/projects/[^/]+", parsed.path
    ):
        resource = parsed.hostname.removesuffix(".services.ai.azure.com")
        if resource and "." not in resource:
            return f"https://{resource}.cognitiveservices.azure.com"
    raise ValueError(
        "PROJECT_ENDPOINT must be a Foundry URL like "
        "https://<resource>.services.ai.azure.com/api/projects/<project> "
        "or a Speech URL like https://<resource>.cognitiveservices.azure.com."
    )


def main() -> None:
    with DefaultAzureCredential() as credential:
        speech_config = speechsdk.SpeechConfig(
            token_credential=credential,
            endpoint=speech_endpoint(),
        )
        speech_config.speech_recognition_language = os.getenv("SPEECH_LANGUAGE", "en-US")
        audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_config
        )

        done = threading.Event()
        transcripts: list[str] = []
        errors: list[str] = []

        def on_recognized(event) -> None:
            if event.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                transcripts.append(event.result.text)
                print(f"\nRecognized: {event.result.text}", flush=True)

        def on_canceled(event) -> None:
            if event.reason == speechsdk.CancellationReason.Error:
                errors.append(event.error_details)
            done.set()

        recognizer.recognized.connect(on_recognized)
        recognizer.canceled.connect(on_canceled)
        recognizer.session_stopped.connect(lambda event: done.set())

        try:
            recognizer.start_continuous_recognition_async().get()
            print("Listening... speak into your microphone. Press Ctrl+C to stop.")
            while not done.wait(0.2):
                pass
        except KeyboardInterrupt:
            print("\nStopped.")
        finally:
            recognizer.stop_continuous_recognition_async().get()

    if errors:
        raise RuntimeError(f"Speech recognition failed: {errors[0]}")

    if transcripts:
        output = SCRIPT_DIR / os.getenv("OUTPUT_TXT", "output.txt")
        output.write_text("\n".join(transcripts) + "\n", encoding="utf-8")
        print(f"Saved transcript to {output}")
    else:
        print("No speech was recognized.")


if __name__ == "__main__":
    main()
