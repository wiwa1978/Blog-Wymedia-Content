"""Query recent Foundry spans from the connected Application Insights resource."""
import json
import os
from datetime import timedelta

from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
from dotenv import load_dotenv

load_dotenv()


QUERY = """
union withsource=TableName isfuzzy=true requests, dependencies, traces
| where timestamp > ago(1h)
| extend source = case(
    TableName == "requests", "requests",
    TableName == "dependencies", "dependencies",
    "traces"
)
| project timestamp, name=coalesce(name, message),
    duration, operation_Id, custom_dimensions=customDimensions,
    target, data, resultCode, success, id,
    source
| order by timestamp asc
"""


def message_preview(attributes: object, key: str, limit: int = 120) -> str | None:
    if not attributes:
        return None
    if isinstance(attributes, str):
        try:
            attributes = json.loads(attributes)
        except json.JSONDecodeError:
            return None
    if not isinstance(attributes, dict):
        return None

    raw_messages = attributes.get(key)
    if not raw_messages:
        return None
    try:
        messages = json.loads(raw_messages) if isinstance(raw_messages, str) else raw_messages
    except json.JSONDecodeError:
        return None

    text_parts: list[str] = []
    for message in messages if isinstance(messages, list) else []:
        for part in message.get("parts", []) if isinstance(message, dict) else []:
            text = part.get("content") or part.get("text")
            if text:
                text_parts.append(str(text))
    if not text_parts:
        return "[content not captured by telemetry]"
    return " ".join(text_parts)[:limit]


def main() -> None:
    resource_id = os.environ["APPINSIGHTS_RESOURCE_ID"]
    result = LogsQueryClient(DefaultAzureCredential()).query_resource(
        resource_id,
        QUERY,
        timespan=timedelta(hours=1),
    )
    if result.status != LogsQueryStatus.SUCCESS:
        raise RuntimeError(f"Application Insights query failed: {result}")

    table = result.tables[0]
    print(f"Trace records returned: {len(table.rows)}")
    for row in table.rows:
        values = dict(zip(table.columns, row))
        print(
            f"{values['timestamp']} | {values['source']} | "
            f"{values['name']} | duration={values['duration']} | "
            f"operation_id={values['operation_Id']}"
        )
        for field in ("target", "data", "resultCode", "success", "id"):
            if values.get(field) not in (None, ""):
                print(f"  {field}={values[field]}")
        if values.get("custom_dimensions"):
            print(f"  attributes={values['custom_dimensions']}")
            prompt_preview = message_preview(
                values["custom_dimensions"], "gen_ai.input.messages"
            )
            response_preview = message_preview(
                values["custom_dimensions"], "gen_ai.output.messages"
            )
            if prompt_preview:
                print(f"  prompt_preview={prompt_preview}")
            if response_preview:
                print(f"  response_preview={response_preview}")


if __name__ == "__main__":
    main()
