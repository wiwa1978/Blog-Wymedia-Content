# Realtime microphone sample

This sample captures live microphone audio, sends it to a Microsoft Foundry realtime GPT deployment, and plays the spoken response through the default speakers.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python .\realtime_microphone.py
```

Set `PROJECT_ENDPOINT` and `MODEL` in `.env`. The microphone must provide audio that can be opened at 24 kHz, mono, 16-bit PCM; `sounddevice` requests that format from the operating system.

Press `Ctrl+C` to stop the client.
