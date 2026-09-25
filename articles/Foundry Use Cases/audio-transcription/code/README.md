# Audio transcription

This sample streams a WAV file to a Microsoft Foundry realtime deployment, plays the source audio locally, prints the transcription, and saves it to `output.txt`.

Run it from this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python .\transcribe_audio.py
```

Set `INPUT_WAV` in `.env` to another 24 kHz, mono, 16-bit PCM WAV file if needed.

The `openai[realtime]` dependency installs the WebSocket support required by `client.realtime.connect(...)`.
