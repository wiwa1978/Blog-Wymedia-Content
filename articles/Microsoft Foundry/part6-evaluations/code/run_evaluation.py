"""Start an evaluation run over an uploaded dataset and poll its status."""
import os
import time
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

load_dotenv()


def main() -> None:
    project = AIProjectClient(endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"], credential=DefaultAzureCredential())
    client = project.get_openai_client()
    run = client.evals.runs.create(eval_id=os.environ["FOUNDRY_EVALUATION_ID"], name="nightly-regression", data_source={"type": "azure_ai_target_completions", "source": {"type": "file_id", "id": os.environ["FOUNDRY_DATASET_ID"]}, "input_messages": {"type": "template", "template": [{"type": "message", "role": "user", "content": {"type": "input_text", "text": "{{item.query}}"}}]}, "target": {"type": "azure_ai_agent", "name": os.environ["FOUNDRY_AGENT_NAME"], "version": os.getenv("FOUNDRY_AGENT_VERSION", "1")}})
    print(f"Evaluation run started: {run.id}")
    while getattr(run, "status", "") in {"queued", "in_progress", "running"}:
        time.sleep(5)
        run = client.evals.runs.retrieve(eval_id=os.environ["FOUNDRY_EVALUATION_ID"], run_id=run.id)
    print(f"Evaluation run finished: {run.status}; inspect per-row results in Foundry")


if __name__ == "__main__":
    main()
