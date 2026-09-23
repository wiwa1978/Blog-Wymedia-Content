"""Upload a JSONL evaluation dataset using the Foundry project client."""
import os
import sys
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

load_dotenv()


def main(path: str) -> None:
    project = AIProjectClient(endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"], credential=DefaultAzureCredential())
    dataset = project.datasets.upload_file(name="agent-regression", version="1", file_path=path)
    print(f"Uploaded dataset {dataset.name} version {dataset.version} id={dataset.id}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "test-queries.jsonl")
