"""List Insights for a monitor and optionally mark one as resolved.

Requires FOUNDRY_INSIGHT_MONITOR_ID. Run this after 02_run_on_demand.py, or
any time after a scheduled run has produced results.

Listing and printing always runs. Resolving an Insight only runs if you set
FOUNDRY_INSIGHT_ID in .env to an ID printed by this script on a prior run.
This mirrors the article: review the evidence before you change status.
"""

import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import AgentInsightStatus, AgentInsightUpdate
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

insights = list(monitor_operations.list_insights(monitor_id, include_details=True))
print(f"Insights available: {len(insights)}")

for insight in insights:
    print(f"\n{insight.id}: {insight.title}")
    print(f"Severity: {insight.severity}; status: {insight.status}")
    print(f"Linked traces: {insight.trace_count}")
    if insight.details:
        print(insight.details.recommended_actions.proposed_fix.text)

insight_id = os.environ.get("FOUNDRY_INSIGHT_ID")
if insight_id:
    resolved_insight = monitor_operations.update_insight(
        monitor_id,
        insight_id,
        AgentInsightUpdate(status=AgentInsightStatus.RESOLVED),
    )
    print(f"\nInsight {insight_id} status: {resolved_insight.status}")
else:
    print("\nSet FOUNDRY_INSIGHT_ID in .env to resolve a specific Insight.")

project_client.close()
credential.close()
