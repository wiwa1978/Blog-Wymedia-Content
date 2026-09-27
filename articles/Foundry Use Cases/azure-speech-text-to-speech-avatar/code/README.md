# Azure Speech text to speech avatar

This standalone Python sample submits a script to Azure Speech batch avatar synthesis, polls for completion, and downloads the resulting MP4. It reads the Foundry `PROJECT_ENDPOINT` from `.env` and converts its resource hostname into a Speech REST endpoint. Batch avatar synthesis itself does not accept the `/api/projects/...` URL. It authenticates with Microsoft Entra ID, not a Speech key.

From this directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `PROJECT_ENDPOINT` in `.env` to your Foundry project URL. For example, `https://my-resource.services.ai.azure.com/api/projects/my-project` maps to `https://my-resource.cognitiveservices.azure.com`. The resource must support Speech batch avatars in a [supported region](https://learn.microsoft.com/azure/ai-services/speech-service/regions?tabs=ttsavatar). If Speech is a separate connected resource or uses a different custom subdomain, set `PROJECT_ENDPOINT` to that Speech resource's `https://<resource>.cognitiveservices.azure.com` URL instead.

Sign in with `az login` (or provide another identity supported by `DefaultAzureCredential`); your identity needs the **Cognitive Services Speech User** or **Cognitive Services Speech Contributor** role on the Speech resource. Edit `prompt.txt`, then run:

```powershell
python .\text_to_speech_avatar.py
```

The MP4 is saved in this directory as `avatar-<job-id>.mp4`. The signed download URL expires; the local video is yours to keep. Each run creates a billable batch synthesis job. If a run times out, the job ID printed to the terminal can be used to check its status with the [GET batch synthesis API](https://learn.microsoft.com/azure/ai-services/speech-service/text-to-speech-avatar/batch-synthesis-avatar).

Run the offline sample tests with `python -m unittest -q test_text_to_speech_avatar`.
