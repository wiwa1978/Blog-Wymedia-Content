"""Enable, inspect, or disable recurring Insights generation.

Requires FOUNDRY_INSIGHT_MONITOR_ID. By default this enables a 6-hour
schedule. Pass "disable" as the first argument to turn scheduling back off,
which is the safest way to leave the sample: enabling a schedule can start a
run immediately and continues to incur model charges after your session ends.

Usage:
    python 04_schedule_monitor.py           # enable a 6-hour schedule
    python 04_schedule_monitor.py disable   # disable the schedule
"""

import os
import sys

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import AgentInsightMonitorUpdate
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

if len(sys.argv) > 1 and sys.argv[1].lower() == "disable":
    monitor_operations.update(monitor_id, AgentInsightMonitorUpdate(enabled=False))
    print("Schedule disabled. This does not cancel an already-active run.")
else:
    scheduled_monitor = monitor_operations.update(
        monitor_id,
        AgentInsightMonitorUpdate(enabled=True, run_interval_hours=6),
    )
    print(f"Schedule enabled: {scheduled_monitor.enabled}")
    print(f"Run interval hours: {scheduled_monitor.run_interval_hours}")
    print(f"Next scheduled run: {scheduled_monitor.next_scheduled_run_at}")
    print("\nRun 'python 04_schedule_monitor.py disable' when you are done.")

project_client.close()
credential.close()
