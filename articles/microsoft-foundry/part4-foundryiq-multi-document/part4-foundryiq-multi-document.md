---
title: "Foundry IQ with multiple documents"
excerpt: "Extend a Foundry IQ RAG pipeline to multiple PDFs with token-aware chunking, document identity, and document-level access control."
slug: microsoft-foundry/part4-foundryiq-multi-document
artifactPath: "microsoft-foundry/part4-foundryiq-multi-document"
tags: []
series: {"slug":"microsoft-foundry","title":"Microsoft Foundry","part":4}
publishAt: "2026-09-18T10:18:00.000Z"
---
# Part 4 - Foundry IQ with multiple documents

In [Part 3 - Foundry IQ with one document](/blog/microsoft-foundry/part3-foundryiq-rag) we built a complete RAG pipeline from one PDF: Azure AI Search stores the chunks and vectors, Foundry IQ turns the index into a reusable knowledge base, and a Foundry agent queries it through MCP.

That walkthrough is a good starting point, but production knowledge rarely lives in one file. This part extends the same pipeline to multiple PDFs and adds the metadata and filtering needed to keep document identity and access boundaries intact.

The complete runnable example is in the [`code`](code) folder:

- [`04_multi_document_index.py`](code/04_multi_document_index.py) builds a separate multi-document index with token-aware chunks and access-control metadata.
- [`05_knowledge_base_with_filters.py`](code/05_knowledge_base_with_filters.py) creates the corresponding Foundry IQ knowledge source and knowledge base, then tests document-level filtering.

This part assumes the Azure resource, model deployments, Search service, managed identities, RBAC, virtual environment, and `.env` configuration from Part 3 are already in place. It reuses the same Azure services but creates separate `-v2` index, knowledge-source, and knowledge-base names so the original single-document example remains available for comparison.

## What changes when there is more than one document?

The basic RAG flow stays the same, but every chunk now needs enough metadata to answer three questions:

1. Which document did this chunk come from?
2. Where in that document did it come from?
3. Which callers are allowed to retrieve it?

Part 4 addresses those questions with a stable `document_id`, a human-readable `document_name`, token-aware chunking, and filterable fields such as `security_group` and `department`.

## Required permissions

The managed-identity permissions are the same as in Part 3. The Azure AI Search service identity needs **Cognitive Services OpenAI User** and **Cognitive Services User** on the Foundry resource. The Foundry project's managed identity needs **Search Index Data Reader** on the Search service. If you see `Could not complete model action`, check the service-side model permissions and allow time for new role assignments to propagate.

## Step 4 — Run `04_multi_document_index.py`

Steps 1-3 prove the pipeline end to end with the simplest possible index: one PDF, character-based chunking, no document identity, no access-control metadata. That's fine for a demo, but a few gaps show up quickly in a real application. `04_multi_document_index.py` addresses four of them at once, building a second, separate index so you can compare it with Step 1's:

### 4a. Give every chunk a stable document identity

Step 1's index has no notion of "which file" a chunk came from — there is only ever one PDF. This script derives a stable `document_id` from the filename and stores it alongside a human-readable `document_name`:

```python
def document_id_for(pdf_path) -> str:
    return pdf_path.stem


document_id = document_id_for(pdf_path)
chunk_id = f"{document_id}_{page_number}_{chunk_index}"
```

Both fields are added to the index schema as filterable, retrievable fields, and later passed to the knowledge source's `source_data_fields` in Step 5, so citations can say *which file* an answer came from — not just which page.

#### As uploaded to the index (Step 4)

Here is a real chunk record produced by the script, exactly as it's uploaded to the index:

```json
{
  "id": "quantum-computing-rag-test_1_0",
  "document_id": "quantum-computing-rag-test",
  "document_name": "quantum-computing-rag-test.pdf",
  "page_number": 1,
  "security_group": "general",
  "department": "research",
  "text": "Quantum Computing: How It Works and Where It Can Help\nExecutive summary\nQuantum computing is a new model of computing that uses quantum-mechanical effects to process information. Classical computers store information as..."
}
```

Notice that `document_id` and `document_name` are **not** appended to the `text` field itself — the chunk text is exactly what came off the PDF page, untouched. Document identity lives in its own metadata fields alongside the text, the same way `page_number` does. That separation matters: it's what lets you filter or cite by document without the model ever seeing "noise" injected into the content it's answering from, and it's what Step 5's `source_data_fields` and `filter_add_on` operate on.

Compare that with [Part 3's chunk record](/blog/microsoft-foundry/part3-foundryiq-rag#as-uploaded-to-the-index-step-1), which only ever had `page_number` and `text` — there was no document to identify because the index only ever held one file.

### 4b. Index every PDF in `data/`, not just the first one

Step 1 calls `find_pdf()`, which returns a single file. This script calls a new helper, `find_all_pdfs()`, and loops over the result:

```python
pdf_paths = find_all_pdfs()

all_chunks: list[dict] = []
for pdf_path in pdf_paths:
    all_chunks.extend(extract_chunks_token_aware(pdf_path))
```

The `data/` folder now has a second PDF, `neuromorphic-computing-rag-test.pdf` (rendered from a markdown source with the same "executive summary + numbered sections" shape as the quantum-computing document, used earlier in this article), so this isn't a hypothetical — the script genuinely indexes a small two-document library. Drop in a third PDF and rerun — no code changes needed.

### 4c. Chunk on tokens, not characters

Step 1's splitter slices raw text every 1,200 *characters*, which can cut a word in half — the article's [concrete chunking example](#extract-and-chunk-the-pdf) shows exactly where that happens. The deeper issue is that "characters" isn't the unit the embedding model actually works in: embedding models have *token* limits, not character limits, so a character count is only a rough proxy for how much content is really in a chunk — it varies with vocabulary, punctuation density, and language. This script uses `tiktoken`, the same tokenizer family the embedding model consumes, and slices on token boundaries instead, so the chunk-size parameter means what it says and the word-splitting failure mode goes away:

```python
import tiktoken

_encoding = tiktoken.get_encoding("cl100k_base")

tokens = _encoding.encode(text)
chunk_tokens = tokens[start : start + CHUNK_SIZE_TOKENS]
chunk_text = _encoding.decode(chunk_tokens).strip()
```

This doesn't guarantee chunks break on sentence boundaries (that would need a layout- or sentence-aware splitter), but it does mean the chunk size is measured in the same unit the model actually sees, and the character-level word-splitting problem goes away.

### 4d. Tag every chunk with access-control metadata

Finally, each chunk gets a `security_group` and `department` field, looked up from a small metadata table keyed by filename:

```python
DOCUMENT_METADATA: dict[str, dict[str, str]] = {
    "quantum-computing-rag-test.pdf": {"security_group": "general", "department": "research"},
    "neuromorphic-computing-rag-test.pdf": {"security_group": "confidential", "department": "research"},
}
DEFAULT_METADATA = {"security_group": "general", "department": "engineering"}
```

In a real system this metadata would come from wherever document permissions already live — a manifest file, a database, a document-management system — not a Python dict. It's inlined here so the example stays self-contained, but the two entries are deliberately different: this is what makes Step 5's access-control demo actually mean something, instead of a single document that's either visible or not. Both fields are marked `filterable` in the index schema, which is what makes them usable as a knowledge-source filter in Step 5.

For this example, the intended access rules are:

| Caller security group | Can access | Cannot access |
| --- | --- | --- |
| `general` | Quantum Computing | Neuromorphic Computing |
| `confidential` | Neuromorphic Computing | Quantum Computing |

Keep these two rules in mind when you run Step 5. The script asks the same questions as both callers and verifies both the allowed and denied paths.

Run it:

```bash
python 04_multi_document_index.py
```

```text
Found 2 PDF(s): neuromorphic-computing-rag-test.pdf, quantum-computing-rag-test.pdf
  neuromorphic-computing-rag-test.pdf: 9 chunks
  quantum-computing-rag-test.pdf: 21 chunks
Embedding 30 chunks across 2 document(s)...
Index 'foundry-iq-rag-index-v2' created or updated successfully.
Uploaded 30 chunks (0 failed).
```

Token-aware chunking produced 21 chunks from the quantum-computing PDF that produced 27 character-based chunks in Step 1 — a reminder that "chunk size" means something slightly different depending on whether you're counting characters or tokens.

> **Note — why the two documents don't produce a proportional number of chunks.** The quantum-computing PDF (8 pages, ~4,400 tokens total) produces 21 chunks, while the shorter neuromorphic-computing PDF (5 pages, ~2,100 tokens total) produces only 9 — not because anything went wrong, but because chunking resets per page: each page is split independently into non-overlapping (well, 50-token-overlapping) windows of 300 tokens, so a page with ~500-650 tokens yields 2-3 chunks. The neuromorphic PDF's last page has only about 50 tokens of text, so it becomes a single small chunk instead of a full one. Fewer pages and less text per page add up to roughly half the chunk count. If you see an unexpectedly low chunk count for one of your own documents, check the token count per page rather than assuming a bug.

## Step 5 — Run `05_knowledge_base_with_filters.py`

Step 4 prepared the searchable data. Step 5 is where that data becomes a Foundry IQ knowledge layer that an agent could use.

This script does three things:

1. It creates (or updates) a knowledge source that points at the Step 4 Azure AI Search index.
2. It creates (or updates) a knowledge base that uses that knowledge source and the existing Azure OpenAI deployment to synthesize grounded answers.
3. It calls the knowledge base's retrieval endpoint directly as two simulated callers, so we can test document-level filtering before adding an agent to the picture.

It does **not** upload the PDFs again, create another search index, or create a `KnowledgeAgent`. The index and chunks come from Step 4; this script adds the Foundry IQ objects and exercises their retrieval behavior. Running Step 4 first is therefore required:

```bash
python 04_multi_document_index.py
python 05_knowledge_base_with_filters.py
```

The two simulated callers are not real identities yet. They simply represent the value that an application would normally resolve from the signed-in user's permissions, such as a Microsoft Entra ID security group. The point of the four test calls is to prove both sides of the boundary: a `general` caller can retrieve the general document but not the confidential one, while a `confidential` caller gets the opposite result. Testing this directly makes it easier to distinguish a search/filtering problem from a later agent-integration problem.

> **If a later call reports `Could not complete model action`.** There are two separate authentication hops here. Your local `DefaultAzureCredential` authenticates the Python client to Azure AI Search, but the model action is executed by the Azure AI Search service itself. Search therefore needs its managed identity to have **Cognitive Services OpenAI User** (and **Cognitive Services User**) on the Foundry resource. If the first retrieval succeeds and a later one fails with `The service failed to authenticate to the model endpoint`, the configuration is usually valid but the service-side model call was transiently rejected; retry the script once. If it persists, check those role assignments, confirm that `AOAI_RESOURCE_URI` points to the same Foundry resource as the deployment, and allow time for a newly added role assignment to propagate. This error occurs before answer synthesis, so it is different from a filter that matches zero documents.

### 5a. Reference the new fields in the knowledge source

The knowledge source's `source_data_fields` now includes `document_id` and `document_name`, so retrieval references identify the source file:

```python
search_index_parameters=SearchIndexKnowledgeSourceParameters(
    search_index_name=SEARCH_INDEX_NAME_V2,
    semantic_configuration_name=SEMANTIC_CONFIG_NAME,
    source_data_fields=[
        SearchIndexFieldReference(name="page_chunk"),
        SearchIndexFieldReference(name="page_number"),
        SearchIndexFieldReference(name="document_id"),
        SearchIndexFieldReference(name="document_name"),
    ],
)
```

### 5b. Apply a per-caller filter at retrieval time

`SearchIndexKnowledgeSourceParameters` supports a `base_filter` — a default filter condition baked into the knowledge source itself. This example leaves that unset and instead applies a filter per request, through `filter_add_on` on `SearchIndexKnowledgeSourceParams`:

```python
from azure.search.documents.knowledgebases import KnowledgeBaseRetrievalClient
from azure.search.documents.knowledgebases.models import (
    KnowledgeBaseMessage,
    KnowledgeBaseMessageTextContent,
    KnowledgeBaseRetrievalRequest,
    SearchIndexKnowledgeSourceParams,
)

client = KnowledgeBaseRetrievalClient(
    endpoint=SEARCH_ENDPOINT,
    credential=DefaultAzureCredential(),
    knowledge_base_name=KNOWLEDGE_BASE_NAME_V2,
)

request = KnowledgeBaseRetrievalRequest(
    messages=[KnowledgeBaseMessage(role="user", content=[KnowledgeBaseMessageTextContent(text=question)])],
    knowledge_source_params=[
        SearchIndexKnowledgeSourceParams(
            knowledge_source_name=KNOWLEDGE_SOURCE_NAME_V2,
            filter_add_on=f"security_group eq '{security_group}'",
        )
    ],
)

response = client.retrieve(request)
```

This is the important distinction for access control: the knowledge source and knowledge base don't decide who can see what. The *caller* — an agent, an API, your own backend — passes the caller's security group on every retrieval call, and Azure AI Search enforces it before any content reaches the model. A fixed `base_filter` on the knowledge source is useful for an organization-wide floor (for example, always excluding a `department`), while `filter_add_on` is what scopes a single request to a single caller.

Run it:

```bash
python 05_knowledge_base_with_filters.py
```

```text
--- Caller in security group 'general' asks: 'What is quantum entanglement?' ---
Answer: Quantum entanglement is a quantum property where the state of each qubit
cannot be fully described independently of the others...
Referenced 12 chunk(s):
  - quantum-computing-rag-test.pdf (page 2)
  - quantum-computing-rag-test.pdf (page 8)
  ...

--- Caller in security group 'general' asks: 'Why is energy efficiency the main argument for neuromorphic computing?' ---
Answer: I don't have access to information that answers this question from the retrieved documents.
Referenced 0 chunks - this caller's filter matched no documents.

--- Caller in security group 'confidential' asks: 'What is quantum entanglement?' ---
Answer: I don't have access to information in the retrieved documents that answers your question.
Referenced 0 chunks - this caller's filter matched no documents.

--- Caller in security group 'confidential' asks: 'Why is energy efficiency the main argument for neuromorphic computing?' ---
Answer: Energy efficiency is the main argument for neuromorphic computing because
these systems are designed to do work only when there is useful input, rather than
continuously processing on a global clock like conventional computers...
Referenced 9 chunk(s):
  - neuromorphic-computing-rag-test.pdf (page 2)
  - neuromorphic-computing-rag-test.pdf (page 4)
  ...
```

The same two questions are asked as both callers. The results confirm the access rules from Step 4:

| Caller security group | Can access | Cannot access | Observed result |
| --- | --- | --- | --- |
| `general` | Quantum Computing | Neuromorphic Computing | Quantum answer returned with references; neuromorphic question returned 0 chunks |
| `confidential` | Neuromorphic Computing | Quantum Computing | Neuromorphic answer returned with references; quantum question returned 0 chunks |

Neither denied result is the model refusing. Azure AI Search simply never returns chunks that don't match the caller's `filter_add_on`, so the boundary holds in both directions, not just as a single access-denied edge case.

## Knowledge versus web search, file search, and MCP

I quite frequently get questions from readers who are confused about how Foundry IQ's knowledge base relates to the other retrieval options already available in Foundry — web search, file search, and MCP servers. It's a fair question: they all let an agent "look something up" before answering, so the boundaries aren't obvious at first glance. Here's how they actually differ:

| Capability | Best for |
| --- | --- |
| Web search | Current public information |
| File search | A small set of files managed in a Foundry vector store |
| Custom function | Deterministic application logic |
| MCP server | External tools and data sources exposed through a standard protocol |
| Foundry IQ | Reusable, permission-aware knowledge bases backed by enterprise search |

Foundry IQ is not just another way to upload a file. It gives you control over the search index, semantic configuration, vector search, citation fields, retrieval instructions, and the model used for agentic retrieval. It is a better fit when the knowledge layer needs to be shared by multiple agents or integrated with an existing Azure AI Search estate.

## Closing thoughts

Adding a second document changes the design from “retrieve from a file” to “retrieve from a governed document collection.” Azure AI Search still stores and retrieves the chunks, but document identity and filterable metadata now become part of the contract between the index, the knowledge source, and the application supplying the caller's security context.
