"""Create or reuse Application Insights for the monitoring walkthrough."""
import os
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.mgmt.applicationinsights import ApplicationInsightsManagementClient
from azure.mgmt.applicationinsights.models import ApplicationInsightsComponent
from azure.mgmt.loganalytics import LogAnalyticsManagementClient
from azure.mgmt.loganalytics.models import Workspace
from azure.core.exceptions import ResourceNotFoundError
from dotenv import load_dotenv, set_key


CODE_DIR = Path(__file__).resolve().parent
ENV_FILE = CODE_DIR / ".env"
load_dotenv(ENV_FILE)


def ensure_log_analytics_workspace(
    la_client: LogAnalyticsManagementClient,
    resource_group: str,
    workspace_name: str,
    location: str,
) -> Workspace:
    try:
        workspace = la_client.workspaces.get(resource_group, workspace_name)
        print(f"Log Analytics workspace already exists: {workspace_name}")
        return workspace
    except ResourceNotFoundError:
        poller = la_client.workspaces.begin_create_or_update(
            resource_group_name=resource_group,
            workspace_name=workspace_name,
            parameters=Workspace(location=location),
        )
        workspace = poller.result()
        print(f"Created Log Analytics workspace: {workspace_name}")
        return workspace


def main() -> None:
    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    resource_group = os.environ["AZURE_RESOURCE_GROUP"]
    location = os.environ["AZURE_LOCATION"]
    foundry_resource = os.environ["AZURE_FOUNDRY_RESOURCE_NAME"]
    app_insights_name = os.getenv(
        "AZURE_APPLICATION_INSIGHTS_NAME",
        f"{foundry_resource}-appinsights",
    )
    workspace_name = os.getenv(
        "AZURE_LOG_ANALYTICS_WORKSPACE_NAME",
        f"{foundry_resource}-logs",
    )

    credential = DefaultAzureCredential()

    la_client = LogAnalyticsManagementClient(
        credential=credential,
        subscription_id=subscription_id,
    )
    workspace = ensure_log_analytics_workspace(la_client, resource_group, workspace_name, location)

    client = ApplicationInsightsManagementClient(
        credential=credential,
        subscription_id=subscription_id,
    )

    try:
        component = client.components.get(resource_group, app_insights_name)
        print(f"Application Insights already exists: {app_insights_name}")
    except ResourceNotFoundError:
        component = client.components.create_or_update(
            resource_group_name=resource_group,
            resource_name=app_insights_name,
            insight_properties=ApplicationInsightsComponent(
                location=location,
                kind="web",
                application_type="web",
                workspace_resource_id=workspace.id,
            ),
        )
        print(f"Created Application Insights: {app_insights_name}")

    if not component.connection_string:
        raise RuntimeError(
            f"Application Insights '{app_insights_name}' did not return a connection string."
        )

    set_key(str(ENV_FILE), "APPLICATIONINSIGHTS_CONNECTION_STRING", component.connection_string)
    app_insights_resource_id = (
        f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
        f"/providers/Microsoft.Insights/components/{app_insights_name}"
    )
    set_key(str(ENV_FILE), "APPINSIGHTS_RESOURCE_ID", app_insights_resource_id)
    print("Saved APPLICATIONINSIGHTS_CONNECTION_STRING to .env")
    print("Saved APPINSIGHTS_RESOURCE_ID to .env")
    print()
    print("Next, associate this Application Insights resource with the Foundry resource")
    print("in the Foundry portal (Agents > Traces > Connect). Then run 02_model_call.py or 03_agent_call.py.")


if __name__ == "__main__":
    main()
