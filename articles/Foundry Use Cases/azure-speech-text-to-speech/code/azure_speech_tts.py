"""Synthesize a text file to MP3 with Azure Speech in Foundry Tools."""

import html
import os
from pathlib import Path
from urllib.parse import urlsplit

import azure.cognitiveservices.speech as speechsdk
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")


def required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or (value.startswith("<") and value.endswith(">")):
        raise ValueError(f"Set {name} in {HERE / '.env'} or in your environment.")
    return value


def speech_endpoint_from_project(project_endpoint: str) -> str:
    parsed = urlsplit(project_endpoint)
    suffix = ".services.ai.azure.com"
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.netloc != parsed.hostname
        or not parsed.hostname.endswith(suffix)
        or parsed.query
        or parsed.fragment
        or len(parsed.path.rstrip("/").split("/")) != 4
        or not parsed.path.startswith("/api/projects/")
    ):
        raise ValueError(
            "PROJECT_ENDPOINT must be a Foundry project URL like "
            "https://<resource>.services.ai.azure.com/api/projects/<project>."
        )
    resource = parsed.hostname[: -len(suffix)]
    if not resource:
        raise ValueError("PROJECT_ENDPOINT must identify a Foundry resource.")
    return f"https://{resource}.cognitiveservices.azure.com/"


def main() -> None:
    endpoint = speech_endpoint_from_project(required_setting("PROJECT_ENDPOINT"))
    voice = os.getenv("VOICE", "en-US-AvaNeural").strip()
    style = os.getenv("STYLE", "").strip()
    rate = os.getenv("RATE", "0%").strip()
    pitch = os.getenv("PITCH", "0%").strip()
    volume = os.getenv("VOLUME", "0%").strip()
    if not voice:
        raise ValueError("VOICE cannot be empty.")

    text_path = HERE / os.getenv("TEXT_FILE", "prompt.txt")
    text = text_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"{text_path} is empty.")

    speech_config = speechsdk.SpeechConfig(
        token_credential=DefaultAzureCredential(), endpoint=endpoint
    )
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz128KBitRateMonoMp3
    )

    content = (
        f'<prosody rate="{html.escape(rate, quote=True)}" '
        f'pitch="{html.escape(pitch, quote=True)}" '
        f'volume="{html.escape(volume, quote=True)}">'
        f"{html.escape(text)}</prosody>"
    )
    if style:
        content = (
            f'<mstts:express-as style="{html.escape(style, quote=True)}">'
            f"{content}</mstts:express-as>"
        )
    ssml = (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        'xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="en-US">'
        f'<voice name="{html.escape(voice, quote=True)}">{content}</voice>'
        "</speak>"
    )

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=None
    )
    result = synthesizer.speak_ssml_async(ssml).get()
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        details = result.cancellation_details
        raise RuntimeError(
            f"Speech synthesis failed: {details.reason}; {details.error_details}"
        )
    if not result.audio_data:
        raise RuntimeError("Speech synthesis completed without audio.")

    output_path = HERE / os.getenv("OUTPUT_FILE", "speech.mp3")
    output_path.write_bytes(bytes(result.audio_data))
    print(f"Saved audio to {output_path}")


if __name__ == "__main__":
    main()
