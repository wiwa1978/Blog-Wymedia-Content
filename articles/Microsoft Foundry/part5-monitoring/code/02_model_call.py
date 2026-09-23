"""Send one direct model request and print client-side timing and usage.

This is a model call, not an agent call, so it intentionally has no
``agent_reference``. Application Insights is only needed to export and retain
the telemetry for cloud-side viewing; the response already contains usage,
and the script measures elapsed time locally.
"""
import os
import sys
import time
from importlib import import_module

from dotenv import load_dotenv

load_dotenv()
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

configure_tracing = import_module("01_configure_tracing").configure_tracing
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential


def main() -> None:
    project = AIProjectClient(
        endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential(),
    )
    client = project.get_openai_client()
    prompt = "In one sentence, explain why request traces are useful."
    started = time.perf_counter()
    response = client.responses.create(
        model=os.environ["MODEL_DEPLOYMENT"],
        input=prompt,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    print(f"Model response ID: {response.id}")
    print(f"Model latency: {elapsed_ms:.0f} ms")
    print(f"Model output: {response.output_text}")
    usage = getattr(response, "usage", None)
    if usage:
        print(
            "Model tokens: "
            f"input={getattr(usage, 'input_tokens', None)} "
            f"output={getattr(usage, 'output_tokens', None)} "
            f"total={getattr(usage, 'total_tokens', None)}"
        )


if __name__ == "__main__":
    configure_tracing()
    main()
