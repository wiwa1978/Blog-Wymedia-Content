---
title: "Foundry IQ with one document"
excerpt: "Build a retrieval-augmented generation pipeline from one PDF with Azure AI Search, Foundry IQ, and Microsoft Foundry Agent Service."
slug: microsoft-foundry/part3-foundryiq-rag
artifactPath: "microsoft-foundry/part3-foundryiq-rag"
tags: ["azure", "ai-foundry", "foundry-iq", "rag", "azure-ai-search", "python", "agents", "mcp"]
series: {"slug":"microsoft-foundry","title":"Microsoft Foundry","part":3}
publishAt: "2026-07-07T10:10:00.000Z"
---
# Part 3 - Foundry IQ with one document

In [Part 1 - Getting Started with the Microsoft Foundry SDK](/blog/microsoft-foundry/part1-getting-started) we created the Foundry resource, project, model deployment, and first agent. In [Part 2 - Beyond the basics](/blog/microsoft-foundry/part2-tools-mcp-memory) we added tools, MCP servers, toolboxes, and memory.

There is one important capability we have not explored yet: **knowledge**.

An agent can call a web search tool for public, current information. It can also use a small managed vector store through file search. But production applications often need a more deliberate retrieval pipeline: extract content from documents, split it into useful chunks, create embeddings, search those chunks, and ground the final answer in the retrieved evidence.

This is the problem addressed by **retrieval-augmented generation (RAG)**. In this post we build that pipeline with:

1. A [PDF about quantum computing](code/data/quantum-computing-rag-test.pdf).
2. Azure AI Search for chunk storage, keyword search, semantic ranking, and vector search.
3. Foundry IQ to represent the searchable content as a reusable knowledge source and knowledge base.
4. Microsoft Foundry Agent Service, connected to the knowledge base through its MCP endpoint.

The complete runnable example is in the [`code`](code) folder:

- [`01_create_search_index.py`](code/01_create_search_index.py) extracts, chunks, embeds, and uploads the PDF.
- [`02_create_knowledge_base.py`](code/02_create_knowledge_base.py) creates the Foundry IQ knowledge source and knowledge base.
- [`03_agent_with_knowledge.py`](code/03_agent_with_knowledge.py) creates an agent and starts an interactive question-and-answer session.

## Putting it all together

Before getting into the details, here is the complete flow. It is intentionally split into three scripts so each resource is visible:

```text
PDF
  |
  v
01_create_search_index.py
  - extract text
  - chunk pages
  - create embeddings
  - create Azure AI Search index
  - upload chunks and vectors
  |
  v
02_create_knowledge_base.py
  - create search index knowledge source
  - create Foundry IQ knowledge base
  |
  v
03_agent_with_knowledge.py
  - create ProjectManagedIdentity connection
  - create Foundry agent with MCPTool
  - ask grounded questions
```

This is also a useful development sequence. You can inspect the raw index independently, validate the knowledge base independently, and only then attach an agent.


## First understand the execution order

There are two different kinds of work in this example:

1. **Azure setup**, which happens before the Python scripts. You create the
   Foundry resource and project, deploy the chat and embedding models, create
   an Azure AI Search service, configure managed identities and RBAC, and place
   a PDF in the `data` folder.
2. **Pipeline setup**, which happens when you run the three Python files. The
   scripts create an index inside the existing Search service, create a
   knowledge base on top of that index, and finally connect an agent to the
   knowledge base.

Azure AI Search is not installed by `01_create_search_index.py`. The Search
service must already exist. That script creates an **index within the service**.
Likewise, the Foundry resource and model deployments must already exist before
the scripts call them.

Run the files in this order:

| Order | File | What it creates or does |
| --- | --- | --- |
| 0 | Azure portal/CLI | Foundry resource, project, model deployments, Search service, identities, and RBAC |
| 1 | [`01_create_search_index.py`](code/01_create_search_index.py) | Reads the PDF locally, chunks and embeds it, creates a Search index, and uploads the chunks |
| 2 | [`02_create_knowledge_base.py`](code/02_create_knowledge_base.py) | Creates a Foundry IQ knowledge source and knowledge base in the existing Search service |
| 3 | [`03_agent_with_knowledge.py`](code/03_agent_with_knowledge.py) | Creates the project connection, creates the agent, and starts interactive Q&A |

The words “chunk” and “embed” describe preprocessing performed by the first
script; they do not mean that an Azure AI Search service is being provisioned
at that point.

Once you have this one-document pipeline working, [Part 4 - Foundry IQ with
multiple documents](/blog/microsoft-foundry/part4-foundryiq-multi-document)
extends it to a whole folder of PDFs with token-aware chunking, document
identity, and document-level access control.

## What is Foundry IQ?

Foundry IQ is the managed knowledge layer for Microsoft Foundry agents. It is built on Azure AI Search's agentic retrieval capabilities.

Azure AI Search and Foundry IQ are related, but they are not the same product:

```text
Azure AI Search service
└── Search index
    ├── Chunk text
    ├── Embedding vectors
    └── Metadata such as page number
        ^
        │ referenced by
        │
Foundry IQ knowledge source
└── Foundry IQ knowledge base
    └── MCP endpoint used by the Foundry agent
```

The **Azure AI Search service** is the Azure resource that stores and queries
indexes. The **index** is a search structure inside that service. In this
article, the index holds the PDF chunks, their embedding vectors, and page
metadata.

**Foundry IQ** sits above that index. It registers the index as a knowledge
source, adds retrieval and answer-generation instructions, optionally
orchestrates multiple knowledge sources, and exposes the resulting knowledge
base through an MCP endpoint that an agent can call.

Another way to think about the boundary is:

| Layer | Responsibility |
| --- | --- |
| Azure AI Search | Store and retrieve indexed text and vectors |
| Foundry IQ knowledge source | Describe how one Search index should be used |
| Foundry IQ knowledge base | Plan retrieval and synthesize grounded answers |
| Foundry agent | Decide when to call the knowledge base and present the answer |

The main concepts are:

- A **search index** contains the searchable chunks and their metadata.
- A **knowledge source** describes how a particular index should be used, including which fields contain answer content and citation data.
- A **knowledge base** combines one or more knowledge sources with retrieval and answer-generation instructions.
- An agent connects to the knowledge base through an MCP endpoint. The knowledge base exposes the `knowledge_base_retrieve` tool.

This separation is useful. The index is a data structure, the knowledge source is a retrieval boundary, and the knowledge base is the reusable knowledge capability that agents can consume.

## Prerequisites

You need:

- An Azure subscription and an existing Microsoft Foundry resource and project from Part 1.
- A deployed chat model, such as `gpt-5.4-mini`.
- A deployed embedding model. This example uses `text-embedding-3-small`.
- An Azure AI Search service.
- Azure CLI authentication:

```bash
az login
```

The example uses Microsoft Entra ID through `DefaultAzureCredential`; it does not use API keys.

Create a virtual environment and install the dependencies:

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

The important packages are:

```text
azure-ai-projects>=2.3.0
azure-identity
azure-search-documents==12.1.0b2
openai
pypdf
python-dotenv
requests
```

The Azure AI Search package is pinned to a preview version because the knowledge source and knowledge base APIs are preview features in this walkthrough.

## Configure the example

Copy the settings into a `.env` file in the `code` folder:

```dotenv
AZURE_AI_PROJECT_ENDPOINT=https://<foundry-resource>.services.ai.azure.com/api/projects/<project-name>
AZURE_AI_PROJECT_RESOURCE_ID=/subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.CognitiveServices/accounts/<foundry-resource>/projects/<project-name>
AZURE_FOUNDRY_RESOURCE_NAME=<foundry-resource>
MODEL_DEPLOYMENT=gpt-5.4-mini
EMBEDDING_MODEL=text-embedding-3-small

AZURE_SEARCH_ENDPOINT=https://<search-service>.search.windows.net
SEARCH_INDEX_NAME=foundry-iq-rag-index
KNOWLEDGE_SOURCE_NAME=foundry-iq-rag-ks
KNOWLEDGE_BASE_NAME=foundry-iq-rag-kb
PROJECT_CONNECTION_NAME=foundry-iq-kb-connection
AGENT_NAME=KnowledgeAgent
```

Place a PDF in the `data` subfolder. The script automatically uses the first `.pdf` file it finds there. You can also set an explicit path with `PDF_PATH`.

## Required permissions

There are two managed identities involved in the pipeline:

1. The Azure AI Search service identity calls the Foundry resource for embeddings and answer synthesis.
2. The Foundry project identity reads the search index when the agent invokes the knowledge base.

Grant the search service identity these roles on the Foundry resource:

- **Cognitive Services OpenAI User**
- **Cognitive Services User**

Grant the Foundry project's managed identity this role on the Azure AI Search service:

- **Search Index Data Reader**

The identity creating the project connection also needs permission to manage Foundry project connections, such as **Foundry Project Manager**.

The exact role-assignment commands depend on your subscription, resource group, resource names, and managed-identity principal IDs. The Azure portal or Azure CLI can be used to apply them.

## Step 1 — Run `01_create_search_index.py`

The first Python file performs three related jobs: local PDF preprocessing,
Search index creation, and document upload. The next sections explain those
jobs in the order they appear in the script.

### 1a. Extract and chunk the PDF

The first script uses `pypdf` to extract text page by page. Each page is split into overlapping 1,200-character chunks with a 200-character overlap.

```python
from pypdf import PdfReader

def extract_chunks(pdf_path):
    reader = PdfReader(str(pdf_path))
    chunks = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        start = 0

        while start < len(text):
            end = start + 1200
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "page_number": page_number,
                    "text": chunk_text,
                })
            if end >= len(text):
                break
            start = end - 200

    return chunks
```

Here is a concrete example from the [sample quantum-computing document](code/data/quantum-computing-rag-test.md). The source
contains this paragraph on page 1:

> Quantum computing is a new model of computing that uses quantum-mechanical effects to process information. Classical computers store information as bits, where each bit is either 0 or 1. Quantum computers store information as quantum bits, or qubits, which can be prepared and manipulated in ways that do not have a direct everyday equivalent. The most important quantum properties are superposition, entanglement, interference, and measurement. Together, these properties allow certain algorithms to explore mathematical structures differently from classical algorithms.

The script extracts the complete page as text and then applies the 1,200-character
window across that page. That means the paragraph is stored together with nearby
content rather than as an isolated paragraph. The first two records produced by
the script look like this (shortened here for readability):

```text
Chunk 1 (page 1, characters 0-1199)
Quantum Computing: How It Works and Where It Can Help
Executive summary
Quantum computing is a new model of computing that uses quantum-mechanical
effects to process information. Classical computers store information as bits,
where each bit is either 0 or 1. Quantum computers store information as quantum
bits, or qubits, which can be prepared and manipulated in ways that do not have
...

Chunk 2 (page 1, characters 1000-2199)
...omputing becomes interesting when a problem has a structure that quantum
algorithms can exploit: factoring large numbers, simulating molecules,
optimizing complex systems, sampling from difficult probability distributions,
or solving certain linear algebra subroutines.
The field is still early. Today's machines are often described as noisy
intermediate-scale quantum devices.
...
```

The second chunk starts 200 characters before the end of the first one. That
overlap gives retrieval some context if an important sentence sits near a
boundary. The example intentionally uses a simple character-based splitter,
which is easy to understand but can split words, as the shortened `...omputing`
example shows. A production splitter should usually respect sentences, tokens,
headings, or document layout.

#### As uploaded to the index (Step 1)

Chunk 1 is actually just this dict — a `page_number` and the `text`, nothing else:

```json
{
  "page_number": 1,
  "text": "Quantum Computing: How It Works and Where It Can Help\nExecutive summary\nQuantum computing is a new model of computing that uses quantum-mechanical effects to process information. Classical computers store information as bits, where each bit is either 0 or 1. Quantum computers store information as quantum bits, or qubits..."
}
```

There is no `document_id`, `document_name`, `security_group`, or `department` field — Step 1's index only ever holds one file, so there was nothing to identify or filter by. [Part 4 - Foundry IQ with multiple documents](/blog/microsoft-foundry/part4-foundryiq-multi-document) adds exactly those four fields once the index has to represent more than one document.

Chunking is deliberately simple here so the mechanics are visible. A production pipeline might use a layout-aware parser, token-based chunk sizes, headings, tables, document identifiers, and richer citation metadata.

### 1b. Create embeddings

Each chunk needs a vector representation for similarity search. The example calls the embedding deployment on the resource-level Azure OpenAI endpoint using Entra ID:

```python
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

credential = DefaultAzureCredential()
embedding_client = AzureOpenAI(
    azure_endpoint="https://<foundry-resource>.cognitiveservices.azure.com",
    api_version="2024-10-21",
    azure_ad_token_provider=get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default",
    ),
)

response = embedding_client.embeddings.create(
    model="text-embedding-3-small",
    input=[chunk["text"] for chunk in chunks],
)
embeddings = [item.embedding for item in response.data]
```

`text-embedding-3-small` produces 1,536-dimensional vectors, so the Azure AI Search vector field must be configured with `1536` dimensions.

For example, the first eight values of the real vectors generated for the
first two chunks of the sample PDF look like this:

```text
Chunk 1: [
  -0.04046631,  0.02809143, -0.00524902,  0.02362061,
   0.03985596, -0.01296997, -0.05319214,  0.07293701,
  ... 1,528 more values
]

Chunk 2: [
  -0.01638794,  0.02333069,  0.00952911,  0.02076721,
   0.02691650, -0.01350403, -0.04119873,  0.03506470,
  ... 1,528 more values
]
```

Each complete vector contains 1,536 floating-point values. The individual
numbers do not have a human-readable meaning such as “topic” or “page”; their
meaning comes from the vector as a whole. Texts with related meaning tend to
produce vectors that are close together in this 1,536-dimensional space. Azure
AI Search uses that property to find relevant chunks when a user asks a
question.

> Why use a resource-level client here? The Foundry project OpenAI-compatible endpoint is ideal for agent and Responses API calls. The embedding deployment is addressed reliably through the resource-level Azure OpenAI endpoint, while still using Entra authentication.

### 1c. Create an Azure AI Search index and upload the chunks

An **Azure AI Search service** is the Azure resource that provides search
capabilities. An **index** is a named, structured collection inside that
service. It is similar to a database table designed for search: the index
defines the fields, data types, filters, ranking configuration, and vector
search settings that Azure AI Search should use.

In this example:

- The Search **service** is the existing Azure resource identified by
  `AZURE_SEARCH_ENDPOINT`.
- The Search **index** is named `foundry-iq-rag-index`.
- Each PDF **chunk** becomes one document (one row-like record) in that index.
- The index schema tells Search which fields contain readable text, embeddings,
  and citation metadata.

The index is not the PDF itself and it is not another language model. It is the
search-optimized representation of the PDF content. The knowledge source and
knowledge base created later point to this index when they need to retrieve
relevant chunks.

The index contains four fields:

- `id` identifies each chunk.
- `page_chunk` contains the human-readable text used for retrieval and answer grounding.
- `page_embedding` contains the embedding vector.
- `page_number` provides citation context.

The index also has a semantic configuration and an Azure OpenAI vectorizer:

```python
from azure.search.documents.indexes.models import (
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    HnswAlgorithmConfiguration,
    SearchField,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    VectorSearch,
    VectorSearchProfile,
)

index = SearchIndex(
    name="foundry-iq-rag-index",
    fields=[
        SearchField(
            name="id",
            type="Edm.String",
            key=True,
            filterable=True,
            sortable=True,
        ),
        SearchField(
            name="page_chunk",
            type="Edm.String",
            searchable=True,
            retrievable=True,
        ),
        SearchField(
            name="page_embedding",
            type="Collection(Edm.Single)",
            searchable=True,
            retrievable=False,
            stored=False,
            vector_search_dimensions=1536,
            vector_search_profile_name="hnsw-profile",
        ),
        SearchField(
            name="page_number",
            type="Edm.Int32",
            filterable=True,
            retrievable=True,
        ),
    ],
    vector_search=VectorSearch(
        profiles=[
            VectorSearchProfile(
                name="hnsw-profile",
                algorithm_configuration_name="hnsw-alg",
                vectorizer_name="aoai-vectorizer",
            )
        ],
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-alg")],
        vectorizers=[
            AzureOpenAIVectorizer(
                vectorizer_name="aoai-vectorizer",
                parameters=AzureOpenAIVectorizerParameters(
                    resource_url="https://<foundry-resource>.services.ai.azure.com",
                    deployment_name="text-embedding-3-small",
                    model_name="text-embedding-3-small",
                ),
            )
        ],
    ),
    semantic_search=SemanticSearch(
        default_configuration_name="semantic-config",
        configurations=[
            SemanticConfiguration(
                name="semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    content_fields=[SemanticField(field_name="page_chunk")]
                ),
            )
        ],
    ),
)
```

The vectorizer is used at query time. The script still uploads the chunk embeddings explicitly because indexing the document vectors and vectorizing a future query are separate operations.

Upload the chunks and vectors with `SearchClient`:

```python
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient

search_client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name="foundry-iq-rag-index",
    credential=DefaultAzureCredential(),
)

documents = [
    {
        "id": str(i),
        "page_chunk": chunk["text"],
        "page_embedding": embedding,
        "page_number": chunk["page_number"],
    }
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
]

search_client.upload_documents(documents=documents)
```

Run the complete first Python file:

```bash
python 01_create_search_index.py
```

For the test PDF used in this series, the script extracted 27 chunks and uploaded all 27 successfully.

## Step 2 — Run `02_create_knowledge_base.py`

The second Python file uses the index created by `01_create_search_index.py`.
It does not read the PDF again and does not create another Search service.

### 2a. Create a Foundry IQ knowledge source

An **indexed knowledge source** is a Foundry IQ knowledge-source type that
wraps an index that already exists in Azure AI Search. “Indexed” means the
content has already been loaded into a Search index and is ready to query; it
does not mean that Foundry IQ is creating or re-indexing the PDF at this
stage.

In this example, `01_create_search_index.py` creates
`foundry-iq-rag-index` and uploads the PDF chunks. The code below registers
that existing index with Foundry IQ and tells it which fields contain the
answer text and citation metadata. Foundry IQ can then use the registered
index as a knowledge source when it plans retrieval.

```python
from azure.search.documents.indexes.models import (
    SearchIndexFieldReference,
    SearchIndexKnowledgeSource,
    SearchIndexKnowledgeSourceParameters,
)

knowledge_source = SearchIndexKnowledgeSource(
    name="foundry-iq-rag-ks",
    description="Chunked PDF content for RAG.",
    search_index_parameters=SearchIndexKnowledgeSourceParameters(
        search_index_name="foundry-iq-rag-index",
        semantic_configuration_name="semantic-config",
        source_data_fields=[
            SearchIndexFieldReference(name="page_chunk"),
            SearchIndexFieldReference(name="page_number"),
        ],
    ),
)

index_client.create_or_update_knowledge_source(knowledge_source)
```

The `source_data_fields` are important. They identify the text that can ground the answer and the metadata that can be used for citations.

### 2b. Create a knowledge base

A knowledge base adds retrieval instructions, answer instructions, an output mode, and the model used for query planning and answer synthesis:

```python
from azure.search.documents.indexes.models import (
    AzureOpenAIVectorizerParameters,
    KnowledgeBase,
    KnowledgeBaseAzureOpenAIModel,
    KnowledgeSourceReference,
)
from azure.search.documents.knowledgebases.models import (
    KnowledgeRetrievalAutoReasoningEffort,
    KnowledgeRetrievalOutputMode,
)

knowledge_base = KnowledgeBase(
    name="foundry-iq-rag-kb",
    description="Answers questions grounded in the indexed PDF.",
    retrieval_instructions=(
        "Use this knowledge source for questions about the indexed PDF."
    ),
    answer_instructions=(
        "Answer concisely and only from retrieved content. Include page numbers."
    ),
    output_mode=KnowledgeRetrievalOutputMode.ANSWER_SYNTHESIS,
    knowledge_sources=[
        KnowledgeSourceReference(name="foundry-iq-rag-ks")
    ],
    models=[
        KnowledgeBaseAzureOpenAIModel(
            azure_open_ai_parameters=AzureOpenAIVectorizerParameters(
                resource_url="https://<foundry-resource>.services.ai.azure.com",
                deployment_name="gpt-5.4-mini",
                model_name="gpt-5.4-mini",
            )
        )
    ],
    retrieval_reasoning_effort=KnowledgeRetrievalAutoReasoningEffort(),
)

index_client.create_or_update_knowledge_base(knowledge_base)
```

Run the complete second Python file:

```bash
python 02_create_knowledge_base.py
```

**What just happened:** Azure AI Search now has a reusable knowledge base that can plan retrieval against the index, synthesize an answer, and expose the retrieval operation as an MCP tool.

## Step 3 — Run `03_agent_with_knowledge.py`

The third Python file uses the knowledge base created by
`02_create_knowledge_base.py`. It creates the connection and agent, then sends
questions to the agent. It does not re-index the PDF.

### 3a. Connect the knowledge base to a Foundry agent

The knowledge base MCP endpoint has this shape:

```text
https://<search-service>.search.windows.net/knowledgebases/<knowledge-base>/mcp?api-version=2026-08-01-preview
```

The official Foundry IQ connection pattern uses a project connection with `ProjectManagedIdentity` authentication. The connection is created through the management-plane REST API:

```python
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import requests

credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(
    credential,
    "https://management.azure.com/.default",
)

connection_url = (
    "https://management.azure.com"
    f"{PROJECT_RESOURCE_ID}/connections/{PROJECT_CONNECTION_NAME}"
    "?api-version=2025-10-01-preview"
)

requests.put(
    connection_url,
    headers={
        "Authorization": f"Bearer {token_provider()}",
        "Content-Type": "application/json",
    },
    json={
        "name": PROJECT_CONNECTION_NAME,
        "type": "Microsoft.MachineLearningServices/workspaces/connections",
        "properties": {
            "authType": "ProjectManagedIdentity",
            "category": "RemoteTool",
            "target": MCP_ENDPOINT,
            "isSharedToAll": True,
            "audience": "https://search.azure.com/",
            "metadata": {"ApiType": "Azure"},
        },
    },
    timeout=30,
).raise_for_status()
```

The agent references that project connection through `MCPTool`:

```python
from azure.ai.projects.models import MCPTool, PromptAgentDefinition

agent = project.agents.create_version(
    agent_name="KnowledgeAgent",
    definition=PromptAgentDefinition(
        model="gpt-5.4-mini",
        instructions=(
            "Use the knowledge base to answer every question. "
            "Never answer from your own knowledge. "
            "If the answer is not in the knowledge base, say: "
            "\"I don't know based on the indexed document.\""
        ),
        tools=[
            MCPTool(
                server_label="knowledge-base",
                server_url=MCP_ENDPOINT,
                require_approval="never",
                allowed_tools=["knowledge_base_retrieve"],
                project_connection_id=PROJECT_CONNECTION_NAME,
            )
        ],
    ),
)
```

Finally, send questions through the Responses API:

```python
conversation = openai.conversations.create()

response = openai.responses.create(
    conversation=conversation.id,
    input="What is quantum entanglement?",
    extra_body={
        "agent_reference": {
            "name": agent.name,
            "type": "agent_reference",
        }
    },
)

print(response.output_text)
```

Run the interactive example:

```bash
python 03_agent_with_knowledge.py
```

The script accepts questions until you type `exit` or `quit`:

```text
Ask questions about the indexed PDF. Type 'exit' to quit.

You: What is quantum entanglement?
Agent: Quantum entanglement is ...
```

In the working test, the answer included Foundry IQ source annotations and identified page 2 as the source.

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

## Next: multiple documents

The multi-document extension, token-aware chunking, and document-level access control are covered in [Part 4 - Foundry IQ with multiple documents](/blog/microsoft-foundry/part4-foundryiq-multi-document).

## What to try next

The single-document walkthrough is a foundation. In Part 4, we extend it to multiple documents, richer metadata, token-aware chunking, and document-level access control.
## Closing thoughts

RAG is the bridge between a general-purpose language model and the information your application actually needs to use. Foundry IQ makes the retrieval layer a first-class, reusable capability: Azure AI Search handles the search foundation, the knowledge base handles retrieval planning and synthesis, and Foundry Agent Service exposes the result to an agent through MCP.

The important design choice is to keep the boundaries clear. Store and search content in Azure AI Search, describe that content with a knowledge source, compose one or more sources into a knowledge base, and let the agent use the knowledge base as a tool.
