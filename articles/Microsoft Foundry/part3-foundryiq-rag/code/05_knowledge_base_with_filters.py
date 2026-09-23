"""
Part 3 - Step 5 (extension): a Foundry IQ knowledge base with document-level filtering.

Building on the index from 04_multi_document_index.py, this script:

  1. Creates a Foundry IQ knowledge source that references document_name and document_id
     in source_data_fields, so retrieval results and citations can say which file an
     answer came from - not just which page.
  2. Creates a knowledge base on top of that knowledge source.
  3. Queries the knowledge base's retrieve endpoint directly (no agent involved) as two
     different simulated callers - one in the "general" security group and one in
     "confidential" - to show that a request-time knowledge-source filter changes what
     comes back, even though both callers ask the exact same question.

This is the "document-level access control" pattern: the knowledge source itself does
not decide who can see what. The caller (an agent, an API, or your own backend) passes
the caller's security group as a filter on every retrieval call, and Azure AI Search
enforces it before any content reaches the model.
"""

from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes.models import (
    AzureOpenAIVectorizerParameters,
    KnowledgeBase,
    KnowledgeBaseAzureOpenAIModel,
    KnowledgeSourceReference,
    SearchIndexFieldReference,
    SearchIndexKnowledgeSource,
    SearchIndexKnowledgeSourceParameters,
)
from azure.search.documents.knowledgebases import KnowledgeBaseRetrievalClient
from azure.search.documents.knowledgebases.models import (
    KnowledgeBaseMessage,
    KnowledgeBaseMessageTextContent,
    KnowledgeBaseRetrievalRequest,
    KnowledgeRetrievalAutoReasoningEffort,
    KnowledgeRetrievalOutputMode,
    SearchIndexKnowledgeSourceParams,
)

from _common import (
    AOAI_RESOURCE_URI,
    KNOWLEDGE_BASE_NAME_V2,
    KNOWLEDGE_SOURCE_NAME_V2,
    MODEL_DEPLOYMENT,
    SEARCH_ENDPOINT,
    SEARCH_INDEX_NAME_V2,
    create_search_index_client,
)

SEMANTIC_CONFIG_NAME = "semantic-config"  # must match 04_multi_document_index.py


def create_knowledge_source(index_client) -> None:
    knowledge_source = SearchIndexKnowledgeSource(
        name=KNOWLEDGE_SOURCE_NAME_V2,
        description=(
            "Multi-document, access-controlled content for the Foundry IQ blog "
            "article's Step 5 extension."
        ),
        search_index_parameters=SearchIndexKnowledgeSourceParameters(
            search_index_name=SEARCH_INDEX_NAME_V2,
            semantic_configuration_name=SEMANTIC_CONFIG_NAME,
            # document_name and document_id are added here (in addition to
            # page_chunk/page_number) so retrieval references can identify which
            # file an answer came from, not just which page of "the" PDF.
            source_data_fields=[
                SearchIndexFieldReference(name="page_chunk"),
                SearchIndexFieldReference(name="page_number"),
                SearchIndexFieldReference(name="document_id"),
                SearchIndexFieldReference(name="document_name"),
            ],
            # No base_filter here: this knowledge source stays "open" by default, and
            # every caller supplies their own scope at query time (see retrieve_as()
            # below). You could instead set base_filter to a fixed floor everyone must
            # satisfy, e.g. "department ne 'legal'", with per-caller filters layered on
            # top of it at request time.
        ),
    )

    index_client.create_or_update_knowledge_source(knowledge_source)
    print(f"Knowledge source '{KNOWLEDGE_SOURCE_NAME_V2}' created or updated successfully.")


def create_knowledge_base(index_client) -> None:
    aoai_params = AzureOpenAIVectorizerParameters(
        resource_url=AOAI_RESOURCE_URI,
        deployment_name=MODEL_DEPLOYMENT,
        model_name=MODEL_DEPLOYMENT,
    )

    knowledge_base = KnowledgeBase(
        name=KNOWLEDGE_BASE_NAME_V2,
        description="Answers questions grounded in an access-controlled document library.",
        retrieval_instructions=(
            "Use this knowledge source for any question about the content of the "
            "indexed documents. Only use content actually returned by retrieval."
        ),
        answer_instructions=(
            "Answer concisely and only from the retrieved content. Cite the document "
            "name and page number(s) the answer came from. If retrieval returns no "
            "content, say you don't have access to information that answers the "
            "question."
        ),
        output_mode=KnowledgeRetrievalOutputMode.ANSWER_SYNTHESIS,
        knowledge_sources=[KnowledgeSourceReference(name=KNOWLEDGE_SOURCE_NAME_V2)],
        models=[KnowledgeBaseAzureOpenAIModel(azure_open_ai_parameters=aoai_params)],
        retrieval_reasoning_effort=KnowledgeRetrievalAutoReasoningEffort(),
    )

    index_client.create_or_update_knowledge_base(knowledge_base)
    print(f"Knowledge base '{KNOWLEDGE_BASE_NAME_V2}' created or updated successfully.")


def retrieve_as(security_group: str, question: str) -> None:
    """Query the knowledge base directly as a caller scoped to one security group.

    The filter is applied through knowledge_source_params.filter_add_on - a per-request
    override that Azure AI Search combines with (or, if set, on top of) any base_filter
    configured on the knowledge source itself. This is what makes the access control
    "document-level": the same knowledge base can serve every caller, but each retrieval
    call only ever sees documents matching that caller's filter.
    """
    client = KnowledgeBaseRetrievalClient(
        endpoint=SEARCH_ENDPOINT,
        credential=DefaultAzureCredential(),
        knowledge_base_name=KNOWLEDGE_BASE_NAME_V2,
    )

    request = KnowledgeBaseRetrievalRequest(
        messages=[
            KnowledgeBaseMessage(
                role="user",
                content=[KnowledgeBaseMessageTextContent(text=question)],
            )
        ],
        output_mode=KnowledgeRetrievalOutputMode.ANSWER_SYNTHESIS,
        knowledge_source_params=[
            SearchIndexKnowledgeSourceParams(
                knowledge_source_name=KNOWLEDGE_SOURCE_NAME_V2,
                filter_add_on=f"security_group eq '{security_group}'",
                include_reference_source_data=True,
            )
        ],
    )

    print(f"\n--- Caller in security group '{security_group}' asks: {question!r} ---")
    response = client.retrieve(request)

    for message in response.response or []:
        for content in message.content:
            if getattr(content, "text", None):
                print(f"Answer: {content.text}")

    if not response.response:
        print("Answer: (no response content - no matching documents were retrievable)")

    references = response.references or []
    if references:
        print(f"Referenced {len(references)} chunk(s):")
        for ref in references:
            source_data = getattr(ref, "source_data", None) or {}
            doc_name = source_data.get("document_name", "unknown")
            page = source_data.get("page_number", "?")
            print(f"  - {doc_name} (page {page})")
    else:
        print("Referenced 0 chunks - this caller's filter matched no documents.")


if __name__ == "__main__":
    index_client = create_search_index_client()
    create_knowledge_source(index_client)
    create_knowledge_base(index_client)

    # quantum-computing-rag-test.pdf is tagged security_group="general" and
    # neuromorphic-computing-rag-test.pdf is tagged security_group="confidential" in
    # 04_multi_document_index.py. Asking the same two questions as both callers shows
    # the boundary working in both directions, not just as an access-denied edge case.
    quantum_question = "What is quantum entanglement?"
    neuromorphic_question = "Why is energy efficiency the main argument for neuromorphic computing?"

    # A "general" caller can see the quantum-computing document...
    retrieve_as("general", quantum_question)
    # ...but not the confidential neuromorphic-computing document.
    retrieve_as("general", neuromorphic_question)

    # A "confidential" caller sees the opposite: nothing on the quantum question...
    retrieve_as("confidential", quantum_question)
    # ...but a grounded, cited answer on the neuromorphic question.
    retrieve_as("confidential", neuromorphic_question)
