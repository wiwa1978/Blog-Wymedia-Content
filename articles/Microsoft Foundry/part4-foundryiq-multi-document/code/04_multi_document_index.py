"""
Part 4 - Step 4: a multi-document, token-aware, access-controlled index.

01_create_search_index.py builds the simplest possible index: one PDF, character-based
chunking, no document identity, no access-control metadata. This script builds a second,
more production-shaped index (SEARCH_INDEX_NAME_V2) that adds four things at once:

  1. Every chunk carries a stable `document_id` and human-readable `document_name`, so a
     citation can say which file an answer came from - not just which page.
  2. Every PDF found in data/ is indexed, not just the first one. Drop more PDFs into
     data/ and rerun this script to grow a small document library.
  3. Chunking is token-aware (tiktoken) instead of character-based, so chunk boundaries
     are measured in the same unit the embedding model actually consumes, and are less
     likely to cut a word in half.
  4. Each chunk also carries a `security_group` field: a filterable attribute that
     05_knowledge_base_with_filters.py uses to scope retrieval to documents a given
     caller is allowed to see.

This script creates a *new* index rather than mutating the one from Step 1, so you can
compare the simple and the extended version side by side.
"""

import tiktoken
from pypdf import PdfReader
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
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

from _common import (
    AOAI_RESOURCE_URI,
    EMBEDDING_MODEL,
    SEARCH_ENDPOINT,
    SEARCH_INDEX_NAME_V2,
    create_embedding_client,
    create_search_index_client,
    find_all_pdfs,
)

# text-embedding-3-small produces 1536-dimensional vectors.
EMBEDDING_DIMENSIONS = 1536
CHUNK_SIZE_TOKENS = 300
CHUNK_OVERLAP_TOKENS = 50
VECTOR_PROFILE_NAME = "hnsw-profile"
VECTORIZER_NAME = "aoai-vectorizer"
SEMANTIC_CONFIG_NAME = "semantic-config"

# In production this metadata would come from a document manifest, a database row, or
# whatever system owns document permissions - not a dict in source code. It is inlined
# here so the demo is self-contained: every PDF in data/ gets tagged with a security
# group and department, falling back to "general"/"engineering" if the filename isn't
# listed explicitly.
DOCUMENT_METADATA: dict[str, dict[str, str]] = {
    "quantum-computing-rag-test.pdf": {"security_group": "general", "department": "research"},
    "neuromorphic-computing-rag-test.pdf": {"security_group": "confidential", "department": "research"},
}
DEFAULT_METADATA = {"security_group": "general", "department": "engineering"}

_encoding = tiktoken.get_encoding("cl100k_base")


def document_id_for(pdf_path) -> str:
    """A stable, filename-derived identifier for a document (no hashing needed - the
    filename stem is already stable across runs, as long as files aren't renamed)."""
    return pdf_path.stem


def extract_chunks_token_aware(pdf_path) -> list[dict]:
    """Return token-aware chunks for one PDF, tagged with document identity and access
    metadata. Unlike 01_create_search_index.py's character-window splitter, chunk
    boundaries here are computed in tokens (the unit the embedding model actually
    consumes), which avoids slicing through the middle of a word."""
    metadata = DOCUMENT_METADATA.get(pdf_path.name, DEFAULT_METADATA)
    document_id = document_id_for(pdf_path)

    reader = PdfReader(str(pdf_path))
    chunks: list[dict] = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue

        tokens = _encoding.encode(text)
        start = 0
        chunk_index = 0
        while start < len(tokens):
            end = start + CHUNK_SIZE_TOKENS
            chunk_tokens = tokens[start:end]
            chunk_text = _encoding.decode(chunk_tokens).strip()
            if chunk_text:
                chunks.append(
                    {
                        "id": f"{document_id}_{page_number}_{chunk_index}",
                        "text": chunk_text,
                        "page_number": page_number,
                        "document_id": document_id,
                        "document_name": pdf_path.name,
                        "security_group": metadata["security_group"],
                        "department": metadata["department"],
                    }
                )
                chunk_index += 1
            if end >= len(tokens):
                break
            start = end - CHUNK_OVERLAP_TOKENS

    return chunks


def embed_chunks(openai_client, chunks: list[dict]) -> list[list[float]]:
    """Embed all chunk texts. Batched in groups of 96 to stay well under the embedding
    API's per-request item limit once a document library grows beyond a single PDF."""
    embeddings: list[list[float]] = []
    batch_size = 96
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[chunk["text"] for chunk in batch],
        )
        embeddings.extend(item.embedding for item in response.data)
    return embeddings


def create_or_update_index(index_client) -> None:
    index = SearchIndex(
        name=SEARCH_INDEX_NAME_V2,
        description=(
            "Multi-document, token-aware, access-controlled index for the Foundry IQ "
            "blog article's Step 4 extension."
        ),
        fields=[
            SearchField(
                name="id",
                type="Edm.String",
                key=True,
                filterable=True,
                sortable=True,
                facetable=True,
            ),
            SearchField(
                name="page_chunk",
                type="Edm.String",
                searchable=True,
                retrievable=True,
                filterable=False,
                sortable=False,
                facetable=False,
            ),
            SearchField(
                name="page_embedding",
                type="Collection(Edm.Single)",
                searchable=True,
                retrievable=False,
                stored=False,
                vector_search_dimensions=EMBEDDING_DIMENSIONS,
                vector_search_profile_name=VECTOR_PROFILE_NAME,
            ),
            SearchField(
                name="page_number",
                type="Edm.Int32",
                filterable=True,
                sortable=True,
                facetable=True,
                retrievable=True,
            ),
            # New in this index: stable document identity for citations.
            SearchField(
                name="document_id",
                type="Edm.String",
                filterable=True,
                sortable=True,
                facetable=True,
                retrievable=True,
            ),
            SearchField(
                name="document_name",
                type="Edm.String",
                filterable=True,
                sortable=True,
                facetable=True,
                retrievable=True,
            ),
            # New in this index: access-control metadata used by the knowledge-source
            # filter in 05_knowledge_base_with_filters.py.
            SearchField(
                name="security_group",
                type="Edm.String",
                filterable=True,
                facetable=True,
                retrievable=True,
            ),
            SearchField(
                name="department",
                type="Edm.String",
                filterable=True,
                facetable=True,
                retrievable=True,
            ),
        ],
        vector_search=VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name=VECTOR_PROFILE_NAME,
                    algorithm_configuration_name="hnsw-alg",
                    vectorizer_name=VECTORIZER_NAME,
                )
            ],
            algorithms=[HnswAlgorithmConfiguration(name="hnsw-alg")],
            vectorizers=[
                AzureOpenAIVectorizer(
                    vectorizer_name=VECTORIZER_NAME,
                    parameters=AzureOpenAIVectorizerParameters(
                        resource_url=AOAI_RESOURCE_URI,
                        deployment_name=EMBEDDING_MODEL,
                        model_name=EMBEDDING_MODEL,
                    ),
                )
            ],
        ),
        semantic_search=SemanticSearch(
            default_configuration_name=SEMANTIC_CONFIG_NAME,
            configurations=[
                SemanticConfiguration(
                    name=SEMANTIC_CONFIG_NAME,
                    prioritized_fields=SemanticPrioritizedFields(
                        content_fields=[SemanticField(field_name="page_chunk")]
                    ),
                )
            ],
        ),
    )

    index_client.create_or_update_index(index)
    print(f"Index '{SEARCH_INDEX_NAME_V2}' created or updated successfully.")


def upload_documents(chunks: list[dict], embeddings: list[list[float]]) -> None:
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=SEARCH_INDEX_NAME_V2,
        credential=DefaultAzureCredential(),
    )

    documents = [
        {
            "id": chunk["id"],
            "page_chunk": chunk["text"],
            "page_embedding": embedding,
            "page_number": chunk["page_number"],
            "document_id": chunk["document_id"],
            "document_name": chunk["document_name"],
            "security_group": chunk["security_group"],
            "department": chunk["department"],
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]

    result = search_client.upload_documents(documents=documents)
    failed = [r for r in result if not r.succeeded]
    print(f"Uploaded {len(documents)} chunks ({len(failed)} failed).")
    for r in failed:
        print(f"  - {r.key}: {r.error_message}")


if __name__ == "__main__":
    pdf_paths = find_all_pdfs()
    print(f"Found {len(pdf_paths)} PDF(s): {', '.join(p.name for p in pdf_paths)}")

    all_chunks: list[dict] = []
    for pdf_path in pdf_paths:
        pdf_chunks = extract_chunks_token_aware(pdf_path)
        print(f"  {pdf_path.name}: {len(pdf_chunks)} chunks")
        all_chunks.extend(pdf_chunks)

    openai_client = create_embedding_client()
    print(f"Embedding {len(all_chunks)} chunks across {len(pdf_paths)} document(s)...")
    embeddings = embed_chunks(openai_client, all_chunks)

    index_client = create_search_index_client()
    create_or_update_index(index_client)
    upload_documents(all_chunks, embeddings)
