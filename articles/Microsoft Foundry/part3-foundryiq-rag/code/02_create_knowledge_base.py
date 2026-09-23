"""
Part 3 - Step 2: Turn the search index into a Foundry IQ knowledge base.

This script:
  1. Wraps the index built in 01_create_search_index.py in a
     SearchIndexKnowledgeSource (Foundry IQ's abstraction over "where the
     content lives").
  2. Creates a KnowledgeBase on top of that knowledge source, pointing at the
     project's chat deployment for query planning and answer synthesis.

The resulting knowledge base exposes a single MCP tool - knowledge_base_retrieve -
that Foundry Agent Service can call. See 03_agent_with_knowledge.py.
"""

from azure.search.documents.indexes.models import (
    AzureOpenAIVectorizerParameters,
    KnowledgeBase,
    KnowledgeBaseAzureOpenAIModel,
    KnowledgeSourceReference,
    SearchIndexFieldReference,
    SearchIndexKnowledgeSource,
    SearchIndexKnowledgeSourceParameters,
)
from azure.search.documents.knowledgebases.models import (
    KnowledgeRetrievalAutoReasoningEffort,
    KnowledgeRetrievalOutputMode,
)

from _common import (
    AOAI_RESOURCE_URI,
    KNOWLEDGE_BASE_NAME,
    KNOWLEDGE_SOURCE_NAME,
    MODEL_DEPLOYMENT,
    SEARCH_INDEX_NAME,
    create_search_index_client,
)

SEMANTIC_CONFIG_NAME = "semantic-config"  # must match 01_create_search_index.py


def create_knowledge_source(index_client) -> None:
    knowledge_source = SearchIndexKnowledgeSource(
        name=KNOWLEDGE_SOURCE_NAME,
        description=(
            "Chunked PDF content used for retrieval-augmented generation (RAG) "
            "demos in the Foundry IQ blog article."
        ),
        search_index_parameters=SearchIndexKnowledgeSourceParameters(
            search_index_name=SEARCH_INDEX_NAME,
            semantic_configuration_name=SEMANTIC_CONFIG_NAME,
            source_data_fields=[
                SearchIndexFieldReference(name="page_chunk"),
                SearchIndexFieldReference(name="page_number"),
            ],
        ),
    )

    index_client.create_or_update_knowledge_source(knowledge_source)
    print(f"Knowledge source '{KNOWLEDGE_SOURCE_NAME}' created or updated successfully.")


def create_knowledge_base(index_client) -> None:
    aoai_params = AzureOpenAIVectorizerParameters(
        # No api_key -> uses the search service's system-assigned managed
        # identity, since the Foundry resource has local (key) auth disabled.
        resource_url=AOAI_RESOURCE_URI,
        deployment_name=MODEL_DEPLOYMENT,
        model_name=MODEL_DEPLOYMENT,
    )

    knowledge_base = KnowledgeBase(
        name=KNOWLEDGE_BASE_NAME,
        description="Answers questions grounded in the indexed PDF content.",
        retrieval_instructions=(
            "Use this knowledge source for any question about the content of "
            "the indexed PDF document."
        ),
        answer_instructions=(
            "Answer concisely and only from the retrieved content. Include the "
            "page number(s) the answer came from."
        ),
        output_mode=KnowledgeRetrievalOutputMode.ANSWER_SYNTHESIS,
        knowledge_sources=[KnowledgeSourceReference(name=KNOWLEDGE_SOURCE_NAME)],
        models=[KnowledgeBaseAzureOpenAIModel(azure_open_ai_parameters=aoai_params)],
        retrieval_reasoning_effort=KnowledgeRetrievalAutoReasoningEffort(),
    )

    index_client.create_or_update_knowledge_base(knowledge_base)
    print(f"Knowledge base '{KNOWLEDGE_BASE_NAME}' created or updated successfully.")


if __name__ == "__main__":
    index_client = create_search_index_client()
    create_knowledge_source(index_client)
    create_knowledge_base(index_client)
