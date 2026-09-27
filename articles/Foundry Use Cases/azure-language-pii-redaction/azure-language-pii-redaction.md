---
title: "Azure Language PII redaction"
excerpt: "Detect and mask personal information in text with Azure Language in Microsoft Foundry. Build a standalone Python script using Entra ID and the synchronous Text PII REST API."
slug: foundry-use-cases/azure-language-pii-redaction
articleId: 367c33c0-0ab2-4d52-811b-de9c0ba14048
artifactPath: "Foundry Use Cases/azure-language-pii-redaction"
tags: ["Microsoft Foundry", "Azure Language", "Python", "PII redaction"]
series: {"slug":"foundry-use-cases","title":"Microsoft Foundry - Use Cases","part":14}
publishAt: "2026-10-07T16:21:00.000Z"
---
# Getting Started: PII Redaction with Azure Language in Microsoft Foundry

Before passing a support ticket or user message to another system, you may want to mask names, phone numbers, and email addresses. Azure Language's **Text PII** capability returns both a redacted copy and a list of detected entities. It is a Language service call, **not a chat-model deployment**; no model name or prompt is required.

This guide builds one small, independent Python program for plain text. Document PII (native files) and Conversation PII (turn-based transcripts) are separate workflows.

## What you need

1. An Azure Language-enabled Foundry/Azure AI Services resource and its **project endpoint**, such as `https://<resource-name>.services.ai.azure.com/api/projects/<project-name>`. The script derives the resource origin from this URL for the Language API.
2. An identity permitted to call the resource (for example, a user granted **Cognitive Services User** on the resource). For local development, sign in with `az login`; in Azure, `DefaultAzureCredential` can use a managed identity. An Azure subscription and access to the Foundry Text PII playground alone do not necessarily grant API access.
3. Python, Azure CLI for local sign-in, and the packages in [`code/requirements.txt`](code/requirements.txt).

```bash
pip install -r code/requirements.txt
az login
```

## Step 1: Authenticate

The REST API accepts a Microsoft Entra bearer token for the Cognitive Services scope:

```python
from azure.identity import DefaultAzureCredential

with DefaultAzureCredential() as credential:
    token = credential.get_token("https://cognitiveservices.azure.com/.default").token
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
```

The final script obtains a fresh token for each run and does not put keys in the repository.

## Step 2: Describe the text to redact

The GA `2026-05-01` API uses `kind: PiiEntityRecognition`. Give each document an ID; the `language` field is set to English here (English is also the default if omitted):

```python
body = {
    "kind": "PiiEntityRecognition",
    "parameters": {"modelVersion": "latest"},
    "analysisInput": {
        "documents": [{
            "id": "1",
            "language": "en",
            "text": "Please call Jane Doe at 555-123-4567.",
        }]
    },
}
```

The default redaction masks detected characters. Detection is statistical: review its output before using it as a privacy or compliance boundary. Supported entities and languages vary.

## Step 3: Call the Language endpoint and read the result

Send the request to the **resource origin** plus `/language/:analyze-text`, not to the project's model endpoint. Extract the origin from `PROJECT_ENDPOINT`:

```python
import requests
from urllib.parse import urlsplit

project_url = urlsplit(project_endpoint)
resource_origin = f"{project_url.scheme}://{project_url.netloc}"
response = requests.post(
    f"{resource_origin}/language/:analyze-text",
    params={"api-version": "2026-05-01"},
    headers=headers,
    json=body,
    timeout=30,
)
response.raise_for_status()
results = response.json()["results"]
if results.get("errors"):
    raise RuntimeError(f"Document analysis failed: {results['errors']}")
document = results["documents"][0]
print(document["redactedText"])
```

`document["redactedText"]` is the service's redacted output, **not a guarantee that every sensitive value was found**. If nothing is detected, the text can remain unchanged. The `entities` array also includes original entity text and positions; avoid sending it to logs or other systems unless necessary. The sample prints category names only.

## Putting it all together

The complete standalone sample is [`code/pii_redaction.py`](code/pii_redaction.py). Copy [`code/.env.example`](code/.env.example) to `code/.env`, then set `PROJECT_ENDPOINT` to your Foundry project endpoint. The sample reads that setting from `.env` beside the script, validates the project URL, and uses its origin for Azure Language. Optionally change `TEXT` (the supplied text is fictional).

From this article's directory:

```bash
python code/pii_redaction.py
```

Example output (the exact entities and masking depend on the service result):

```text
Redacted text: Please call ******** at ************ or email ************************.
Detected categories: Person, PhoneNumber, Email
```

If you receive 401/403, confirm both the signed-in identity and its permissions on the **resource**. If you receive 404, check that `PROJECT_ENDPOINT` points to the intended Foundry project and that the Language capability is available on its resource. The script raises API and per-document errors instead of treating a failed request as successful redaction. A successful request with missed detections still requires your own review and safeguards.

## What to try next

1. Specify a supported language other than English in the document to redact multilingual text.
2. Inspect the response's entity categories and confidence scores in a secure debugging environment (not application logs).
3. Explore `piiCategories` to restrict which entity categories are detected; excluded categories will **not** be masked.
4. Evaluate Document PII for PDF/DOCX or Conversation PII for structured transcripts instead of treating them as plain text.

Text PII gives you an easy synchronous redaction step before downstream processing, provided you handle uncertain detections and raw entity data carefully.

## Microsoft Learn resources

- [Detect and redact personally identifiable information in text](https://learn.microsoft.com/azure/ai-services/language-service/personally-identifiable-information/how-to/redact-text-pii)
- [Text PII overview](https://learn.microsoft.com/azure/ai-services/language-service/personally-identifiable-information/text-pii-overview)
- [Analyze Text REST API](https://learn.microsoft.com/en-us/rest/api/language/analyze-text/analyze-text/analyze-text?view=rest-language-analyze-text-2026-05-01)
