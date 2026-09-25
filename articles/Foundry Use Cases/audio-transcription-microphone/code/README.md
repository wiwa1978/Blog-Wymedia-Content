# Live microphone transcription

This sample captures microphone audio, streams it to a Microsoft Foundry realtime deployment, prints each completed speech turn, and saves the transcript to `output.txt`.

Run it from this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python .\transcribe_microphone.py
```

Speak into the microphone and press `Ctrl+C` to stop. The `openai[realtime]` extra installs the WebSocket support required by `client.realtime.connect(...)`.
