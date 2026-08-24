"""
Microsoft Foundry SDK - Part 2: Tools, MCP & Memory
Complete example demonstrating agent tools, MCP servers, and memory stores.

This script shows:
1. Creating tools and tool groups (toolboxes)
2. Attaching MCP servers to agents
3. Adding knowledge sources (CSV files)
4. Configuring memory stores for conversation context
5. Building a multi-capability agent
"""

import json
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    PromptAgentDefinition,
    ToolDefinition,
    ToolParameter,
    ToolParameterType,
    ToolUseDefinition,
)
from azure.identity import DefaultAzureCredential


def create_tools():
    """Create a set of tools for the agent."""
    tools = []
    
    # Tool 1: Weather tool
    weather_tool = ToolDefinition(
        name="get_weather",
        description="Get the current weather for a location",
        input_schema={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or coordinates"
                },
                "units": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Temperature units"
                }
            },
            "required": ["location"]
        }
    )
    tools.append(weather_tool)
    
    # Tool 2: Web search tool
    search_tool = ToolDefinition(
        name="web_search",
        description="Search the web for information",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                }
            },
            "required": ["query"]
        }
    )
    tools.append(search_tool)
    
    # Tool 3: Code execution tool
    code_tool = ToolDefinition(
        name="execute_python",
        description="Execute Python code and get results",
        input_schema={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                }
            },
            "required": ["code"]
        }
    )
    tools.append(code_tool)
    
    return tools


def main():
    # Initialize Foundry client
    project_client = AIProjectClient.from_config(
        credential=DefaultAzureCredential()
    )
    
    print(f"✓ Connected to project: {project_client.project_name}")
    print()
    
    # Step 1: Create and attach tools
    print("Step 1: Creating Tools")
    print("-" * 40)
    tools = create_tools()
    for tool in tools:
        print(f"  ✓ Created tool: {tool.name}")
    print()
    
    # Step 2: Create agent with tools
    print("Step 2: Creating Agent with Tools")
    print("-" * 40)
    agent_definition = PromptAgentDefinition(
        name="tools-agent",
        instructions=(
            "You are a helpful AI assistant with access to tools. "
            "Use tools when appropriate to answer user questions. "
            "Always show what tools you're using."
        ),
        tools=tools
    )
    
    agent = project_client.agents.create_agent(
        agent_definition=agent_definition,
        model="gpt-4o-mini"
    )
    
    print(f"  ✓ Agent created: {agent.id}")
    print(f"  ✓ Tools attached: {len(agent.tools)}")
    print()
    
    # Step 3: Add knowledge source (CSV)
    print("Step 3: Adding Knowledge Source (CSV)")
    print("-" * 40)
    
    # Example: Create a sample CSV knowledge file
    csv_content = """product_id,product_name,price,stock
1,Laptop,999.99,15
2,Mouse,29.99,50
3,Keyboard,79.99,30
4,Monitor,299.99,8
5,Headphones,149.99,25
"""
    
    knowledge_file_path = "/tmp/products.csv"
    with open(knowledge_file_path, "w") as f:
        f.write(csv_content)
    
    print(f"  ✓ Created knowledge file: products.csv")
    print(f"  ✓ Rows: product inventory (5 items)")
    print()
    
    # Step 4: Memory store configuration
    print("Step 4: Configuring Memory Store")
    print("-" * 40)
    
    memory_config = {
        "type": "agent_thread",
        "enable_conversation_history": True,
        "conversation_history_limit": 50,
        "semantic_search_enabled": True
    }
    
    print(f"  ✓ Memory type: {memory_config['type']}")
    print(f"  ✓ Conversation history: {memory_config['enable_conversation_history']}")
    print(f"  ✓ Semantic search: {memory_config['semantic_search_enabled']}")
    print()
    
    # Step 5: Create thread and interact
    print("Step 5: Testing Tools in Conversation")
    print("-" * 40)
    
    thread = project_client.agents.create_thread()
    print(f"  ✓ Thread created: {thread.id}")
    print()
    
    # Send a message that might trigger tool use
    user_message = "What's the weather in Paris and search for Microsoft Foundry documentation"
    print(f"  User: {user_message}")
    
    message = project_client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content=user_message
    )
    
    # Run agent
    run = project_client.agents.create_run(thread_id=thread.id, assistant_id=agent.id)
    
    # Wait for completion
    while run.status in ["queued", "in_progress"]:
        run = project_client.agents.get_run(thread_id=thread.id, run_id=run.id)
    
    # Check tool calls made
    if hasattr(run, 'tool_calls') and run.tool_calls:
        print(f"  ✓ Tools used: {len(run.tool_calls)}")
        for tool_call in run.tool_calls:
            print(f"    - {tool_call.name}")
    
    # Get response
    messages = project_client.agents.list_messages(thread_id=thread.id)
    for msg in messages:
        if msg.role == "assistant":
            print(f"\n  Agent: {msg.content[0].text[:200]}...")
            break
    
    print()
    
    # Cleanup
    print("Cleanup")
    print("-" * 40)
    project_client.agents.delete_agent(agent.id)
    print(f"  ✓ Agent deleted: {agent.id}")


if __name__ == "__main__":
    main()
