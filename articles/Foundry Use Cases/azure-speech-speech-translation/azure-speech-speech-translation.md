---
title: "Live speech translation with Azure Speech"
excerpt: "Translate microphone speech into another language with Azure Speech in Foundry Tools and a standalone Python Speech SDK sample."
slug: foundry-use-cases/azure-speech-speech-translation
articleId: 0c8dbe56-3c45-469d-87e4-ab72c0355cbd
artifactPath: "Foundry Use Cases/azure-speech-speech-translation"
tags: ["Microsoft Foundry", "Azure Speech", "Python", "speech translation", "microphone"]
series: {"slug":"foundry-use-cases","title":"Microsoft Foundry - Use Cases","part":17}
publishAt: "2026-10-12T16:27:00.000Z"
---
# Getting Started: Live Speech Translation with Azure Speech in Microsoft Foundry

This sample **records live audio from your computer's default microphone** while the script is running, then prints both the recognized speech and its translation in the terminal. It uses **Azure Speech in Foundry Tools** and the Python Speech SDK. Its `TranslationRecognizer` handles microphone capture, streaming, recognition, and translation; you do not need an audio file, web application, or WebSocket proxy. It does not save the microphone audio to disk.

This is **not** the `gpt-realtime-translate` WebSocket model: that model can stream translated audio as well as text and uses a different endpoint and authentication flow. Here we use the dedicated Speech service and print translated **text**. To speak that translation aloud, you can add speech synthesis as a separate step.

## Prerequisites

- A Speech-enabled Foundry resource and its **project endpoint** (`.../api/projects/...`). The script derives the Speech custom-domain endpoint from the project URL. Usage may incur charges.
- An identity assigned the **Cognitive Services Speech User** or **Cognitive Services Speech Contributor** role on that resource. Run `az login` locally (or use another identity supported by `DefaultAzureCredential`). No Speech resource key is required.
- Python and a working default microphone with permission for your terminal to access it.
- The packages in [`code/requirements.txt`](code/requirements.txt): `azure-cognitiveservices-speech`, `azure-identity`, and `python-dotenv`.

The standalone sample consists of [`speech_translation.py`](code/speech_translation.py), [`requirements.txt`](code/requirements.txt), [`.env.example`](code/.env.example), and a [`README`](code/README.md).

## Step 1: Configure the Speech resource

Copy [`code/.env.example`](code/.env.example) to `code/.env` and fill in your resource details:

```dotenv
PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
SOURCE_LANGUAGE=en-US
TARGET_LANGUAGE=fr
```

`PROJECT_ENDPOINT` is the Foundry project URL. The script derives `https://<resource>.cognitiveservices.azure.com/` for the Speech SDK; the project URL itself is **not** a Speech endpoint. The identity selected by `DefaultAzureCredential` must have access to that resource. Neither `SPEECH_KEY` nor `SPEECH_REGION` is needed. `SOURCE_LANGUAGE` is a **recognition locale** such as `en-US`; `TARGET_LANGUAGE` is a **translation language code** such as `fr`. They are not interchangeable. No GPT model deployment is required.

## Step 2: Set up the translation recognizer

Read `PROJECT_ENDPOINT` from `.env`, derive the Speech resource endpoint from its hostname, and initialize `SpeechTranslationConfig` with that endpoint and a Microsoft Entra credential. The Speech SDK handles token acquisition. Specify the spoken language and translation target, then attach the default microphone:

```python
with DefaultAzureCredential() as credential:
    config = speechsdk.translation.SpeechTranslationConfig(
        token_credential=credential, endpoint=speech_endpoint
    )
    config.speech_recognition_language = "en-US"
    config.add_target_language("fr")
    audio = speechsdk.audio.AudioConfig(use_default_microphone=True)
    recognizer = speechsdk.translation.TranslationRecognizer(
        translation_config=config, audio_config=audio
    )
    # Start recognition while the credential remains open.
```

`AudioConfig(use_default_microphone=True)` selects your computer's default input device. The Speech SDK records and streams its live audio for translation; this is **not** translation from a pre-recorded file. In an application that receives raw PCM from a browser, you could instead pass an SDK `PushAudioInputStream`, but that transport and its browser audio plumbing are unnecessary for this local example.

## Step 3: Read completed translations

Continuous recognition sends results to event callbacks. The `recognized` event's `result.text` contains the original speech; `result.translations[target]` holds the translated text. Only `TranslatedSpeech` is a successful translation:

```python
def on_recognized(event) -> None:
    result = event.result
    if result.reason == speechsdk.ResultReason.TranslatedSpeech:
        print(f"Original: {result.text}")
        print(f"French: {result.translations['fr']}")

recognizer.recognized.connect(on_recognized)
recognizer.start_continuous_recognition_async().get()
```

The complete script below also listens for cancellation and session end, stops cleanly on Ctrl+C, and reports missing translations rather than silently claiming success. For provisional subtitles, `recognizing` events are available too; their text can still change, so do not treat it as a final translation.

## Putting it all together

Save this complete script as [`code/speech_translation.py`](code/speech_translation.py), or use the linked file directly:

```python
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
```

## Run it

Open PowerShell in the article's `code` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
az login
# Edit .env with your Foundry project endpoint.
python .\speech_translation.py
```

If you already have a configured `.env`, skip `Copy-Item` to avoid replacing it. The script starts recording from your **default microphone** when it prints `Listening...`. Speak a sentence and pause so the SDK can finalize the utterance; press Ctrl+C to stop recording.

Sample output from a microphone run (the translation may vary):

```text
Listening... speak into your microphone. Press Ctrl+C to stop.

Stopped.

en-US: Hi there I wanted to know if everything works correctly.
fr: Bonjour, je voulais savoir si tout fonctionne correctement.
```

Recognition callbacks run asynchronously, so a final translation can appear just after `Stopped.` If you see an authentication error, check that the identity used by `DefaultAzureCredential` has a Speech User or Speech Contributor role on the resource identified by `PROJECT_ENDPOINT`. If the microphone does not open, check OS microphone permissions and the selected default input device.

## What to try next

1. Change `TARGET_LANGUAGE` to `de` or `nl` and compare the translated text against the [supported languages](https://learn.microsoft.com/azure/ai-services/speech-service/language-support).
2. Call `add_target_language` again for a second target, then print each key in `result.translations`.
3. Subscribe to `recognizing` to display provisional live captions while still using `recognized` for final translations.
4. Use `SpeechSynthesizer` with a suitable target-language voice to turn the translated text into spoken audio; headphones help prevent speaker feedback into the microphone.

The core pattern is **SpeechTranslationConfig -> TranslationRecognizer -> translated results**. It gives you live speech translation without depending on the architecture of a larger application.

## Microsoft Learn resources

- [How to translate speech with Azure Speech](https://learn.microsoft.com/azure/ai-services/speech-service/how-to-translate-speech?pivots=programming-language-python)
- [Microsoft Entra authentication with the Speech SDK](https://learn.microsoft.com/azure/ai-services/speech-service/how-to-configure-azure-ad-auth?pivots=programming-language-python)
- [Speech translation overview](https://learn.microsoft.com/azure/ai-services/speech-service/speech-translation)
- [Speech SDK language support](https://learn.microsoft.com/azure/ai-services/speech-service/language-support)
