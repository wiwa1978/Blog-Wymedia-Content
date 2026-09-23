"""
Part 3 - Step 1: Build a search index for Retrieval-Augmented Generation (RAG).

This script:
  1. Reads a PDF from the data/ folder (see _common.find_pdf()).
  2. Splits its text into overlapping chunks, per page.
  3. Embeds every chunk with the Foundry project's embedding deployment.
  4. Creates (or updates) an Azure AI Search index with a vector field, a
     semantic configuration, and an Azure OpenAI vectorizer (so the knowledge
     base can also embed queries automatically at retrieval time).
  5. Uploads the chunk + embedding documents into that index.

This index is the foundation for the Foundry IQ knowledge source and
knowledge base created in 02_create_knowledge_base.py.
"""

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
    SEARCH_INDEX_NAME,
    create_clients,
    create_embedding_client,
    create_search_index_client,
    find_pdf,
)

# text-embedding-3-small produces 1536-dimensional vectors.
EMBEDDING_DIMENSIONS = 1536
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
VECTOR_PROFILE_NAME = "hnsw-profile"
VECTORIZER_NAME = "aoai-vectorizer"
SEMANTIC_CONFIG_NAME = "semantic-config"


def extract_chunks(pdf_path) -> list[dict]:
    """Return [{"page_number": int, "text": str}, ...] chunks from the PDF."""
    reader = PdfReader(str(pdf_path))
    chunks: list[dict] = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue

        start = 0
        while start < len(text):
            end = start + CHUNK_SIZE
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({"page_number": page_number, "text": chunk_text})
            if end >= len(text):
                break
            start = end - CHUNK_OVERLAP

    return chunks


def embed_chunks(openai_client, chunks: list[dict]) -> list[list[float]]:
    """Embed all chunk texts in a single batched call."""
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[chunk["text"] for chunk in chunks],
    )
    return [item.embedding for item in response.data]


def create_or_update_index(index_client) -> None:
    index = SearchIndex(
        name=SEARCH_INDEX_NAME,
        description=(
            "Chunked, embedded content extracted from a PDF for retrieval-augmented "
            "generation (RAG) demos in the Foundry IQ blog article."
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
                        # No api_key / auth_identity -> the search service's
                        # system-assigned managed identity is used, since the
                        # Foundry resource has local (key) auth disabled.
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
    print(f"Index '{SEARCH_INDEX_NAME}' created or updated successfully.")


def upload_documents(chunks: list[dict], embeddings: list[list[float]]) -> None:
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=SEARCH_INDEX_NAME,
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

    result = search_client.upload_documents(documents=documents)
    failed = [r for r in result if not r.succeeded]
    print(f"Uploaded {len(documents)} chunks ({len(failed)} failed).")
    for r in failed:
        print(f"  - {r.key}: {r.error_message}")


if __name__ == "__main__":
    pdf_path = find_pdf()
    print(f"Reading PDF: {pdf_path.name}")

    chunks = extract_chunks(pdf_path)
    print(f"Extracted {len(chunks)} chunks from {pdf_path.name}")

    project, _ = create_clients()
    openai_client = create_embedding_client()
    print("Embedding chunks...")
    embeddings = embed_chunks(openai_client, chunks)

    index_client = create_search_index_client()
    create_or_update_index(index_client)
    upload_documents(chunks, embeddings)
