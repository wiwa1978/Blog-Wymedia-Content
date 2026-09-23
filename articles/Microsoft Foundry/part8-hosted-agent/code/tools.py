"""
MCP tool definitions for the hosted knowledge agent.

These tools are registered with the agent and available for the model to call
during conversation. Tool schemas are auto-generated from function signatures.
"""
from agent_framework import tool


@tool
def read_markdown_file(file_path: str, max_lines: int = 50) -> str:
    """Read a Markdown file from the local filesystem and return its content.

    This simulates an MCP filesystem tool that a hosted agent can use
    to query local documentation or knowledge bases without exposing
    file paths to direct API calls.

    Args:
        file_path: Path to the Markdown file (relative to the agent's working directory).
        max_lines: Maximum number of lines to return (default 50).

    Returns:
        File content (limited to max_lines) or an error message.
    """
    from pathlib import Path

    try:
        base_dir = Path(__file__).parent.resolve()
        requested_path = Path(file_path)
        resolved_path = (
            requested_path if requested_path.is_absolute() else base_dir / requested_path
        ).resolve()
        print(f"[tool] read_markdown_file: {resolved_path}", flush=True)
        if not resolved_path.exists():
            return f"Error: File not found: {file_path}"
        if not resolved_path.is_file():
            return f"Error: Path is not a file: {file_path}"

        with open(resolved_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[:max_lines]
        return "".join(lines)
    except Exception as exc:
        return f"Error reading file: {exc}"


@tool
def query_json_data(data_type: str, query_field: str = None) -> str:
    """Query structured JSON data and return matching records.

    This simulates an MCP database tool that a hosted agent can use
    to search product catalogs, FAQs, or documentation indexes without
    exposing raw database credentials or APIs.

    Args:
        data_type: Type of data to query (e.g., "products", "faqs", "documentation").
        query_field: Optional field to filter by (e.g., "category=cloud-services").

    Returns:
        JSON data matching the query or an error message.
    """
    import json
    from pathlib import Path

    try:
        # Simulated data sources - replace with actual data lookup
        data_dir = Path(__file__).parent / "data"
        data_file = data_dir / f"{data_type}.json"
        print(f"[tool] query_json_data: {data_file}", flush=True)

        if not data_file.exists():
            return f"Error: No data source found for '{data_type}'"

        with open(data_file, "r", encoding="utf-8") as f:
            all_data = json.load(f)

        # Simple filter if query_field is provided
        if query_field and "=" in query_field:
            field, value = query_field.split("=", 1)
            filtered = [
                item
                for item in all_data
                if isinstance(item, dict) and item.get(field) == value
            ]
            return json.dumps(filtered, indent=2)

        return json.dumps(all_data[:10], indent=2)  # Return first 10 records
    except Exception as exc:
        return f"Error querying data: {exc}"
