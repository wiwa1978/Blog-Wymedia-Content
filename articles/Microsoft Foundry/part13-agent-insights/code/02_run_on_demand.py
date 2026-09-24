"""Run an Insights analysis on demand and print the run summary.

Requires FOUNDRY_INSIGHT_MONITOR_ID to already be set (see 01_create_monitor.py).
Analyzes traces from the last 3 hours. Run time depends on traffic volume,
telemetry completeness, and the selected Judge model.
"""

import os
import uuid

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import AgentInsightRunCreate
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

credential = DefaultAzureCredential()
project_client = AIProjectClient(
    endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    credential=credential,
    allow_preview=True,
)
monitor_operations = project_client.beta.agent_insight_monitors
monitor_id = os.environ["FOUNDRY_INSIGHT_MONITOR_ID"]

poller = monitor_operations.begin_create_run(
    monitor_id,
    AgentInsightRunCreate(lookback_hours=3),
    operation_id=str(uuid.uuid4()),
)
run_id = poller.details["run_id"]
print(f"Run ID: {run_id}")
print("Waiting for the run to complete...")

run_result = poller.result()
completed_run = monitor_operations.get_run(monitor_id, run_id)

print(f"Run status: {completed_run.status}")
print(f"Traces in window: {run_result.traces_in_window}")
print(f"Traces analyzed: {run_result.traces_analyzed}")
print(f"Insights created: {run_result.insights_created}")
print(f"Insights updated: {run_result.insights_updated}")
print(f"Insights reopened: {run_result.insights_reopened}")
print(f"Total tokens: {run_result.token_usage.total_tokens}")

project_client.close()
credential.close()
