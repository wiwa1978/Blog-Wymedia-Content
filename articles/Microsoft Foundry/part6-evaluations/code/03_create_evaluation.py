"""Create the customer-support FAQ evaluation criteria."""
import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import TestingCriterionAzureAIEvaluator as AzureEvaluatorCriterion
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai.types.eval_create_params import TestingCriterionTextSimilarity

load_dotenv()


def main() -> None:
    project = AIProjectClient(
        endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential(),
    )
    model = os.environ["MODEL_DEPLOYMENT"]
    criteria = [
        AzureEvaluatorCriterion(
            type="azure_ai_evaluator",
            name="Coherence",
            evaluator_name="builtin.coherence",
            initialization_parameters={"deployment_name": model},
            data_mapping={"query": "{{item.query}}", "response": "{{sample.output_text}}"},
        ),
        AzureEvaluatorCriterion(
            type="azure_ai_evaluator",
            name="Groundedness",
            evaluator_name="builtin.groundedness",
            initialization_parameters={"deployment_name": model},
            data_mapping={
                "query": "{{item.query}}",
                "response": "{{sample.output_text}}",
                "context": "{{item.context}}",
            },
        ),
        AzureEvaluatorCriterion(
            type="azure_ai_evaluator",
            name="Relevance",
            evaluator_name="builtin.relevance",
            initialization_parameters={"deployment_name": model},
            data_mapping={"query": "{{item.query}}", "response": "{{sample.output_text}}"},
        ),
        AzureEvaluatorCriterion(
            type="azure_ai_evaluator",
            name="Violence",
            evaluator_name="builtin.violence",
            data_mapping={"query": "{{item.query}}", "response": "{{sample.output_text}}"},
        ),
        TestingCriterionTextSimilarity(
            type="text_similarity",
            name="Reference answer similarity",
            input="{{sample.output_text}}",
            reference="{{item.expected_answer}}",
            evaluation_metric="fuzzy_match",
            pass_threshold=0.65,
        ),
    ]
    evaluation = project.get_openai_client().evals.create(
        name="Customer support FAQ regression",
        testing_criteria=criteria,
        data_source_config={
            "type": "custom",
            "item_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "context": {"type": "string"},
                    "expected_answer": {"type": "string"},
                    "category": {"type": "string"},
                },
                "required": ["query", "context", "expected_answer", "category"],
            },
            "include_sample_schema": True,
        },
    )
    print(f"Evaluation created: {evaluation.id}")
    print(f"Add this to .env: FOUNDRY_EVALUATION_ID={evaluation.id}")
    print(f"Or pass it directly: python 04_run_evaluation.py {evaluation.id}")


if __name__ == "__main__":
    main()
