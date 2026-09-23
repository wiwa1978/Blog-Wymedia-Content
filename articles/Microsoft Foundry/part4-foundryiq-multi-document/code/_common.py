"""Shared configuration for the Part 4 (Foundry IQ / RAG) examples."""

import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents.indexes import SearchIndexClient
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

PROJECT_ENDPOINT = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
PROJECT_RESOURCE_ID = os.environ["AZURE_AI_PROJECT_RESOURCE_ID"]
MODEL_DEPLOYMENT = os.getenv("MODEL_DEPLOYMENT", "gpt-5.1-mini")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"].rstrip("/")
SEARCH_INDEX_NAME = os.getenv("SEARCH_INDEX_NAME", "foundry-iq-rag-index")
KNOWLEDGE_SOURCE_NAME = os.getenv("KNOWLEDGE_SOURCE_NAME", "foundry-iq-rag-ks")
KNOWLEDGE_BASE_NAME = os.getenv("KNOWLEDGE_BASE_NAME", "foundry-iq-rag-kb")
PROJECT_CONNECTION_NAME = os.getenv("PROJECT_CONNECTION_NAME", "foundry-iq-kb-connection")
AGENT_NAME = os.getenv("AGENT_NAME", "KnowledgeAgent")

# Used by the 04/05 extension scripts (multi-document, token-aware, filtered index).
# These are a separate index/knowledge source/knowledge base so you can compare the
# Step 1-3 walkthrough with the extended version side by side.
SEARCH_INDEX_NAME_V2 = os.getenv("SEARCH_INDEX_NAME_V2", f"{SEARCH_INDEX_NAME}-v2")
KNOWLEDGE_SOURCE_NAME_V2 = os.getenv("KNOWLEDGE_SOURCE_NAME_V2", f"{KNOWLEDGE_SOURCE_NAME}-v2")
KNOWLEDGE_BASE_NAME_V2 = os.getenv("KNOWLEDGE_BASE_NAME_V2", f"{KNOWLEDGE_BASE_NAME}-v2")

# The Azure OpenAI-compatible endpoint of the parent Foundry resource - used by
# the search index vectorizer (query-time embeddings) and by the knowledge
# base's LLM (query planning + answer synthesis).
AOAI_RESOURCE_URI = f"https://{os.environ['AZURE_FOUNDRY_RESOURCE_NAME']}.services.ai.azure.com"

DATA_DIR = Path(__file__).parent / "data"


def create_clients() -> tuple[AIProjectClient, object]:
    """Create the Foundry project client and its OpenAI-compatible client."""
    project = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )
    return project, project.get_openai_client()


def create_embedding_client() -> AzureOpenAI:
    """Create an Entra-authenticated client for the resource-level embedding deployment."""
    credential = DefaultAzureCredential()
    return AzureOpenAI(
        azure_endpoint=f"https://{os.environ['AZURE_FOUNDRY_RESOURCE_NAME']}.cognitiveservices.azure.com",
        api_version="2024-10-21",
        azure_ad_token_provider=get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        ),
    )


def create_search_index_client() -> SearchIndexClient:
    """Create a keyless (RBAC) client for index/knowledge-source/knowledge-base admin."""
    return SearchIndexClient(endpoint=SEARCH_ENDPOINT, credential=DefaultAzureCredential())


def agent_reference(agent_name: str) -> dict:
    """Return the agent reference payload used by Responses API calls."""
    return {"agent_reference": {"name": agent_name, "type": "agent_reference"}}


def find_pdf() -> Path:
    """Return the PDF to index: PDF_PATH env var, or the first PDF in data/."""
    explicit = os.getenv("PDF_PATH", "").strip()
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(f"PDF_PATH is set but the file doesn't exist: {path}")
        return path

    candidates = sorted(DATA_DIR.glob("*.pdf"))
    if not candidates:
        raise FileNotFoundError(
            f"No PDF found. Drop a .pdf file into {DATA_DIR} or set PDF_PATH in .env."
        )
    return candidates[0]


def find_all_pdfs() -> list[Path]:
    """Return every PDF in data/, sorted by filename, for multi-document indexing."""
    candidates = sorted(DATA_DIR.glob("*.pdf"))
    if not candidates:
        raise FileNotFoundError(
            f"No PDFs found. Drop one or more .pdf files into {DATA_DIR}."
        )
    return candidates
