"""Translate live microphone speech with Azure Speech in Foundry Tools."""

import os
import re
import threading
from pathlib import Path
from urllib.parse import urlsplit

import azure.cognitiveservices.speech as speechsdk
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")


def setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("<"):
        raise ValueError(f"Set {name} in {HERE / '.env'} or your environment.")
    return value


def speech_endpoint_from_project(project_endpoint: str) -> str:
    parsed = urlsplit(project_endpoint.rstrip("/"))
    suffix = ".services.ai.azure.com"
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.netloc != parsed.hostname
        or not parsed.hostname.endswith(suffix)
        or not re.fullmatch(r"/api/projects/[^/]+", parsed.path)
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "PROJECT_ENDPOINT must be a Foundry project URL like "
            "https://<resource>.services.ai.azure.com/api/projects/<project>."
        )
    resource = parsed.hostname.removesuffix(suffix)
    if not resource or "." in resource:
        raise ValueError("PROJECT_ENDPOINT must identify one Foundry resource.")
    return f"https://{resource}.cognitiveservices.azure.com/"


def main() -> None:
    source = setting("SOURCE_LANGUAGE")
    target = setting("TARGET_LANGUAGE")
    with DefaultAzureCredential() as credential:
        config = speechsdk.translation.SpeechTranslationConfig(
            token_credential=credential,
            endpoint=speech_endpoint_from_project(setting("PROJECT_ENDPOINT")),
        )
        config.speech_recognition_language = source
        config.add_target_language(target)
        audio = speechsdk.audio.AudioConfig(use_default_microphone=True)
        recognizer = speechsdk.translation.TranslationRecognizer(
            translation_config=config, audio_config=audio
        )

        done = threading.Event()
        errors: list[str] = []

        def on_recognized(event) -> None:
            result = event.result
            if result.reason == speechsdk.ResultReason.TranslatedSpeech:
                translation = result.translations.get(target)
                if not translation:
                    errors.append(f"No {target} translation was returned.")
                    done.set()
                    return
                print(f"\n{source}: {result.text}\n{target}: {translation}", flush=True)
            elif result.reason == speechsdk.ResultReason.RecognizedSpeech:
                errors.append("Speech was recognized but not translated.")
                done.set()

        def on_canceled(event) -> None:
            if event.reason == speechsdk.CancellationReason.Error:
                errors.append(event.error_details or "Speech translation was canceled.")
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
            raise RuntimeError(f"Speech translation failed: {errors[0]}")


if __name__ == "__main__":
    main()
