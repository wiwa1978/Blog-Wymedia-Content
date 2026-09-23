"""Start an evaluation run over an uploaded dataset and poll its status."""
import os
import statistics
import sys
import time
from collections import defaultdict
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

load_dotenv()


def _percentile(values: list, pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def _print_report(client, eval_id: str, run) -> None:
    counts = run.result_counts
    total = counts.total or 1
    print("\n=== Aggregate results ===")
    print(f"Passed: {counts.passed}/{counts.total}  Failed: {counts.failed}  Errored: {counts.errored}  ({counts.passed / total:.0%} pass rate)")

    print("\n=== Per-criterion results (from the run summary) ===")
    for c in run.per_testing_criteria_results:
        c_total = c.passed + c.failed or 1
        print(f"{c.testing_criteria:35s} passed {c.passed}/{c.passed + c.failed}  ({c.passed / c_total:.0%})")

    # Per-row detail, per-criterion average score, and a latency proxy from row creation timestamps.
    scores_by_criterion = defaultdict(list)
    row_timestamps = []
    print("\n=== Per-row detail ===")
    for item in client.evals.runs.output_items.list(run_id=run.id, eval_id=eval_id):
        row_timestamps.append(item.created_at)
        category = item.datasource_item.get("category", "?")
        line = f"[{item.status:4s}] category={category:20s}"
        for result in item.results:
            scores_by_criterion[result.name].append(result.score)
            mark = "pass" if result.passed else "FAIL"
            line += f"  {result.name}={result.score:.2f}({mark})"
        print(line)

    print("\n=== Per-criterion average score (computed from output items) ===")
    for name, scores in scores_by_criterion.items():
        print(f"{name:35s} avg={statistics.fmean(scores):.2f}  min={min(scores):.2f}  max={max(scores):.2f}  n={len(scores)}")

    if len(row_timestamps) > 1:
        deltas = sorted(b - a for a, b in zip(row_timestamps, row_timestamps[1:]))
        print("\n=== Row-completion spacing (proxy, not a per-request latency measurement) ===")
        print(f"P50={_percentile(deltas, 0.5):.2f}s  P95={_percentile(deltas, 0.95):.2f}s")
        print(
            "Note: the Evaluations API does not report per-request latency. The figures above are the "
            "spacing between consecutive row completions, not the agent's actual response time. For true "
            "P50/P95 request latency, use Application Insights tracing (APPLICATIONINSIGHTS_CONNECTION_STRING)."
        )

    print(f"\nFull report: {run.report_url}")


def main(eval_id: str) -> None:
    if eval_id.startswith("evalrun_"):
        raise SystemExit(
            f"'{eval_id}' looks like a RUN id, not an EVALUATION id.\n"
            "FOUNDRY_EVALUATION_ID must hold the ID printed by 03_create_evaluation.py "
            "(starts with 'eval_'), not the 'Evaluation run started: evalrun_...' line "
            "printed by this script. Re-run 03_create_evaluation.py if you no longer have it."
        )
    project = AIProjectClient(endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"], credential=DefaultAzureCredential())
    client = project.get_openai_client()
    run = client.evals.runs.create(
        eval_id=eval_id,
        name="customer-support-faq-regression",
        data_source={
            "type": "azure_ai_target_completions",
            "source": {"type": "file_id", "id": os.environ["FOUNDRY_DATASET_ID"]},
            "input_messages": {
                "type": "template",
                "template": [
                    {
                        "type": "message",
                        "role": "user",
                        "content": {
                            "type": "input_text",
                            "text": "{{item.query}}\n\nSupport policy:\n{{item.context}}",
                        },
                    }
                ],
            },
            "target": {
                "type": "azure_ai_agent",
                "name": os.environ["FOUNDRY_AGENT_NAME"],
                "version": os.getenv("FOUNDRY_AGENT_VERSION", "1"),
            },
        },
    )
    print(f"Evaluation run started: {run.id}")
    while getattr(run, "status", "") in {"queued", "in_progress", "running"}:
        time.sleep(5)
        run = client.evals.runs.retrieve(eval_id=eval_id, run_id=run.id)
    print(f"Evaluation run finished: {run.status}")
    if run.status == "completed":
        _print_report(client, eval_id, run)
    else:
        print("Run did not complete successfully; inspect the run in Foundry for details.")
        if getattr(run, "error", None):
            print(f"Error: {run.error}")


if __name__ == "__main__":
    evaluation_id = sys.argv[1] if len(sys.argv) > 1 else os.environ["FOUNDRY_EVALUATION_ID"]
    main(evaluation_id)
