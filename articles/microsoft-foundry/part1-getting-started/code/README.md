# Part 1 — Getting Started with the Microsoft Foundry SDK

Runnable scripts matching each step in the article, in order:

| Script | What it does |
|---|---|
| `01_verify_auth.py` | Confirms `DefaultAzureCredential` / `az login` works. |
| `02_create_foundry_resource.py` | Creates the Foundry resource (Cognitive Services account, kind `AIServices`). |
| `03_create_project.py` | Creates a project on that resource. |
| `04_get_project.py` | Reads the project back to confirm it exists. |
| `05_deploy_model.py` | Deploys a model onto the Foundry resource via `CognitiveServicesManagementClient.deployments`. |
| `06_inspect_project.py` | Lists deployed models and connections via `AIProjectClient`. |
| `07_chat.py` | Sends a chat request to a deployed model. |
| `08_create_agent.py` | Creates a versioned prompt agent. |
| `full_example.py` | End-to-end: deploy model + list deployments + one chat call + create agent. |
| `cleanup.py` | Deletes the project(s) and the Foundry resource. |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate    # macOS/Linux

pip install -r requirements.txt
az login

copy .env.example .env
# then edit .env with your subscription id, resource group, resource/project names, endpoint
```

## Run

Each script loads its settings from `.env` via `python-dotenv`.

```bash
python 01_verify_auth.py
python 02_create_foundry_resource.py
python 03_create_project.py
python 04_get_project.py
python 05_deploy_model.py
python 06_inspect_project.py
python 07_chat.py
python 08_create_agent.py
python full_example.py

python cleanup.py
```
