---
title: "Simple Text Chat"
excerpt: "Build a small streaming text-chat application with Microsoft Foundry and Python. The sample uses a Foundry project endpoint, Entra ID authentication, and the OpenAI-compatible chat completions API."
slug: foundry-use-cases/text-chat
articleId: 546bcaae-c35f-4ff1-a0e9-8ebb9d209d05
artifactPath: "Foundry Use Cases/text-chat"
tags: ["Microsoft Foundry", "Azure AI", "Python", "text chat"]
series: {"slug":"foundry-use-cases","title":"Microsoft Foundry - Use Cases","part":1}
publishAt: "2026-09-24T14:43:00.000Z"
---
# Getting Started: Simple Text Chat with Microsoft Foundry

A text chat is one of the smallest useful Foundry applications: send a user message to a deployed model and stream the answer back as it is generated. The same pattern works with current and future chat-capable model deployments because the script reads the deployment name from the environment.

## What you need

1. A **Foundry project** with a chat-capable model deployment. The value sent as `MODEL` must be the exact deployment name shown in the project's **Deployed models** page; it may differ from the underlying model name.
2. **Azure CLI login** (`az login`) with permission to use the project — or another identity supported by `DefaultAzureCredential`.
3. The Python packages listed in [`code/requirements.txt`](code/requirements.txt):

```bash
pip install -r code/requirements.txt
```

## The core idea

The sample uses four steps:

1. **Load configuration** from `.env`, including the Foundry project endpoint and deployment name.
2. **Authenticate with Entra ID** using `DefaultAzureCredential`; no API key is stored in the sample.
3. **Create the project OpenAI client** with `AIProjectClient.get_openai_client()`.
4. **Stream a chat completion** with `chat.completions.create`.

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

with (
    DefaultAzureCredential() as credential,
    AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential) as project_client,
    project_client.get_openai_client() as openai_client,
):
    stream = openai_client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        stream=True,
    )
```

Streaming makes the application feel responsive: tokens are printed as they arrive instead of waiting for the complete answer.

## Configure and run it

Copy [`code/.env.example`](code/.env.example) to `code/.env`, then set `PROJECT_ENDPOINT` and `MODEL`. Set `MODEL` to the exact deployment name shown in the Foundry project's **Deployed models** page. For example, if you created a deployment named `my-gpt-4o-mini`, use `MODEL=my-gpt-4o-mini`; do not assume the base model ID `gpt-4o-mini` is the deployment name.

`PROJECT_ENDPOINT` should be the project endpoint shown in Foundry, for example:

```text
https://<resource-name>.services.ai.azure.com/api/projects/<project-name>
```

Set `PROMPT` for a single response. If `PROMPT` is omitted, the full script starts an interactive terminal chat and keeps the conversation history between turns. `SYSTEM_PROMPT` is optional.

Run the sample from the article's `code` directory:

```bash
python text_chat.py
```

Example output:

```text
Assistant (gpt-6-luna): Microsoft Foundry is Microsoft’s platform for building, testing, deploying, and managing AI applications and agents. It brings together access to AI models, development tools, data connections, evaluation and safety features, and deployment options, so teams can create AI solutions and operate them with enterprise security and governance on Microsoft’s cloud.
```

The attached [`text_chat.py`](code/text_chat.py) is the complete runnable sample and is available in the code modal for viewing or download.

## Microsoft Learn resources

- [Azure AI Projects client library for Python](https://learn.microsoft.com/python/api/overview/azure/ai-projects-readme?view=azure-python) — authenticate with `AIProjectClient` and obtain an OpenAI-compatible client.
- [Use reasoning models with Microsoft Foundry Models](https://learn.microsoft.com/azure/foundry/foundry-models/how-to/use-chat-reasoning) — configure the OpenAI client and send chat completions through a Foundry project endpoint.
- [Chat completions with Azure OpenAI](https://learn.microsoft.com/azure/ai-foundry/openai/how-to/chatgpt) — understand messages, deployments, and streaming responses.
