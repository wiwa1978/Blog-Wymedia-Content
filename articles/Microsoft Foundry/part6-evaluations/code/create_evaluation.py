"""Create an evaluation with built-in and rubric evaluator criteria."""
import os
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import TestingCriterionAzureAIEvaluator
from azure.identity import DefaultAzureCredential

load_dotenv()


def main() -> None:
    project = AIProjectClient(endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"], credential=DefaultAzureCredential())
    model = os.environ["MODEL_DEPLOYMENT"]
    criteria = [
        TestingCriterionAzureAIEvaluator(type="azure_ai_evaluator", name="Coherence", evaluator_name="builtin.coherence", initialization_parameters={"deployment_name": model}, data_mapping={"query": "{{item.query}}", "response": "{{sample.output_text}}"}),
        TestingCriterionAzureAIEvaluator(type="azure_ai_evaluator", name="Violence", evaluator_name="builtin.violence", data_mapping={"query": "{{item.query}}", "response": "{{sample.output_text}}"}),
        # Replace with the name/version of a rubric evaluator created in Foundry.
        TestingCriterionAzureAIEvaluator(type="azure_ai_evaluator", name="Domain rubric", evaluator_name=os.environ["FOUNDRY_RUBRIC_EVALUATOR"], initialization_parameters={"deployment_name": model}, data_mapping={"query": "{{item.query}}", "response": "{{sample.output_text}}"}),
    ]
    evaluation = project.get_openai_client().evals.create(name="Agent regression", testing_criteria=criteria, data_source_config={"type": "custom", "item_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}, "include_sample_schema": True})
    print(f"Evaluation created: {evaluation.id}")


if __name__ == "__main__":
    main()
