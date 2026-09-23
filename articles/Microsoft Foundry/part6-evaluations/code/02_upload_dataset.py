"""Upload a JSONL evaluation dataset using the Foundry project client."""
import os
import sys
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential

load_dotenv()


def main(path: str, version: str) -> None:
    project = AIProjectClient(endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"], credential=DefaultAzureCredential())
    try:
        dataset = project.datasets.upload_file(name="support-faq-regression", version=version, file_path=path)
    except ResourceExistsError:
        raise SystemExit(
            f"Dataset 'support-faq-regression' version '{version}' already exists. Foundry dataset "
            "versions are immutable, so re-uploading the same version fails even if the file content "
            "changed. Pass a new version, e.g. `python 02_upload_dataset.py ./test-queries.jsonl 2`."
        )
    print(f"Uploaded dataset {dataset.name} version {dataset.version} id={dataset.id}")


if __name__ == "__main__":
    args = sys.argv[1:]
    dataset_path = args[0] if len(args) > 0 else "test-queries.jsonl"
    dataset_version = args[1] if len(args) > 1 else "1"
    main(dataset_path, dataset_version)
