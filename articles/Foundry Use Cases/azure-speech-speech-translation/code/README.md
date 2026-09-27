# Azure Speech: live speech translation

This standalone Python sample translates microphone speech into text using the
Azure Speech SDK. It does not require the larger app, a WebSocket proxy, or a
GPT Realtime model deployment.

In PowerShell, from this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `PROJECT_ENDPOINT` in `.env` to the Foundry project URL for a
Speech-enabled resource. The script derives the resource's Speech endpoint
from the project URL; it does not send the project URL directly to the Speech
SDK. Sign in with `az login` using an identity assigned the Cognitive Services
Speech User (or Speech Contributor) role on that resource. The script uses
`DefaultAzureCredential`; no Speech key or region is required.
`SOURCE_LANGUAGE` is a recognition locale (for example, `en-US`);
`TARGET_LANGUAGE` is a translation language code (for example, `fr`). Then run:

```powershell
python .\speech_translation.py
```

Speak into the default microphone and pause between sentences. Final source
text and translated text print in the terminal. Press Ctrl+C to stop. Make sure
your terminal has microphone permissions. Keep `.env` private; do not commit
credentials.
