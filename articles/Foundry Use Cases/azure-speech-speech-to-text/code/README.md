# Azure Speech: live speech to text

Run this standalone microphone sample from this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `PROJECT_ENDPOINT` in `.env` to the Foundry project URL (for example, `https://my-resource.services.ai.azure.com/api/projects/my-project`). The sample derives `https://my-resource.cognitiveservices.azure.com` for the Speech SDK. This assumes Speech is enabled on the **same Foundry resource**; a separately linked Speech resource needs its own endpoint instead. You can also set `PROJECT_ENDPOINT` directly to the Speech resource endpoint. Sign in with `az login` (or another identity supported by `DefaultAzureCredential`) and ensure that identity has the **Cognitive Services Speech User** role on the Speech resource. No API key is needed. Then run:

```powershell
python .\speech_to_text.py
```

Speak into the default microphone. Completed utterances print as they arrive. Press `Ctrl+C` to save them to `output.txt`. Set `SPEECH_LANGUAGE` to a supported locale such as `fr-FR` if needed. Do not commit `.env` or `output.txt`.
