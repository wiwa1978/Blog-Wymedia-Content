"""Create (or reuse) an Insights monitor for an existing registered agent.

Run this first. It creates the monitor with scheduling disabled, so nothing
runs automatically until you explicitly start a scan (see 02_run_on_demand.py)
or enable a schedule (see 04_schedule_monitor.py).
"""

import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import AgentInsightMonitorCreate
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

monitor = monitor_operations.create(
    AgentInsightMonitorCreate(
        agent_name=os.environ["FOUNDRY_AGENT_NAME"],
        model_deployment_name=os.environ["FOUNDRY_MODEL_NAME"],
        enabled=False,
    )
)

print(f"Monitor ID: {monitor.id}")
print("Copy this value into FOUNDRY_INSIGHT_MONITOR_ID in your .env file.")
print("Do not delete this monitor to rerun the samples: deleting it also")
print("removes its runs, Insights, and state.")

project_client.close()
credential.close()
