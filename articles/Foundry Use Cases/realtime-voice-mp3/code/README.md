# Realtime voice sample

This sample sends a WAV audio file to a Microsoft Foundry realtime GPT deployment, saves the model's spoken reply as a WAV file, and writes both the input and reply transcripts to a text file.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python .\realtime_voice.py
```

Set `PROJECT_ENDPOINT` and `MODEL` in `.env`, then set `INPUT_WAV` to your input file. The WAV file must be 24 kHz, mono, 16-bit PCM.

If you only have an MP3, convert it first with FFmpeg:

```powershell
ffmpeg -i input.mp3 -ar 24000 -ac 1 -sample_fmt s16 input.wav
```

The script prints the input transcript and the model's reply transcript to the console, and also writes both to `output.txt`.
