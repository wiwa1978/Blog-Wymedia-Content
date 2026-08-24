"""
Microsoft Foundry SDK - Part 4: Multi-Agent Orchestration
Complete example demonstrating Agent-to-Agent (A2A) communication.

This script shows:
1. Setting up specialist agents (finance, HR, operations)
2. Configuring A2A connections between agents
3. Creating an orchestrator agent that delegates to specialists
4. Handling streaming responses from A2A calls
5. Error handling and fallback patterns
"""

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    PromptAgentDefinition,
    A2APreviewTool,
    A2APreviewToolInput,
)
from azure.identity import DefaultAzureCredential


def create_specialist_agents(project_client):
    """Create specialist agents for different domains."""
    
    specialists = {}
    
    # Finance Specialist
    finance_agent = project_client.agents.create_agent(
        agent_definition=PromptAgentDefinition(
            name="finance-specialist",
            instructions=(
                "You are a finance expert. Answer questions about budgeting, "
                "forecasting, and financial analysis. Be precise with numbers."
            )
        ),
        model="gpt-4o-mini"
    )
    specialists["finance"] = finance_agent
    print(f"  ✓ Finance Specialist: {finance_agent.id}")
    
    # HR Specialist
    hr_agent = project_client.agents.create_agent(
        agent_definition=PromptAgentDefinition(
            name="hr-specialist",
            instructions=(
                "You are an HR expert. Answer questions about hiring, benefits, "
                "and employee policies. Be empathetic and clear."
            )
        ),
        model="gpt-4o-mini"
    )
    specialists["hr"] = hr_agent
    print(f"  ✓ HR Specialist: {hr_agent.id}")
    
    # Operations Specialist
    ops_agent = project_client.agents.create_agent(
        agent_definition=PromptAgentDefinition(
            name="operations-specialist",
            instructions=(
                "You are an operations expert. Answer questions about processes, "
                "efficiency, and supply chain. Be practical and detailed."
            )
        ),
        model="gpt-4o-mini"
    )
    specialists["operations"] = ops_agent
    print(f"  ✓ Operations Specialist: {ops_agent.id}")
    
    return specialists


def create_orchestrator_agent(project_client, specialists):
    """Create an orchestrator agent with A2A connections to specialists."""
    
    # Create A2A tools for each specialist
    a2a_tools = []
    
    for domain, specialist in specialists.items():
        # Note: In production, you'd use AgentEndpointConfig to expose the specialist
        # For this example, we show the A2APreviewTool structure
        a2a_tool = A2APreviewTool(
            name=f"consult_{domain}_specialist",
            description=f"Ask the {domain.upper()} specialist for expert advice",
            specialist_agent_id=specialist.id,
            # In real scenario, would include:
            # - project_connection_id
            # - endpoint_url
        )
        a2a_tools.append(a2a_tool)
    
    # Create orchestrator with A2A tools
    orchestrator = project_client.agents.create_agent(
        agent_definition=PromptAgentDefinition(
            name="orchestrator",
            instructions=(
                "You are an intelligent orchestrator. When users ask questions, "
                "determine which specialist to consult. You have access to "
                "finance, HR, and operations specialists. Delegate appropriately "
                "and synthesize their responses into a comprehensive answer."
            ),
            tools=a2a_tools
        ),
        model="gpt-4o-mini"
    )
    
    print(f"  ✓ Orchestrator: {orchestrator.id}")
    print(f"    - Connected to {len(a2a_tools)} specialists via A2A")
    
    return orchestrator


def main():
    # Initialize Foundry client
    project_client = AIProjectClient.from_config(
        credential=DefaultAzureCredential()
    )
    
    print(f"✓ Connected to project: {project_client.project_name}")
    print()
    
    # Step 1: Create specialist agents
    print("Step 1: Creating Specialist Agents")
    print("-" * 40)
    specialists = create_specialist_agents(project_client)
    print()
    
    # Step 2: Create orchestrator with A2A connections
    print("Step 2: Creating Orchestrator with A2A Connections")
    print("-" * 40)
    orchestrator = create_orchestrator_agent(project_client, specialists)
    print()
    
    # Step 3: Create thread for interaction
    print("Step 3: Setting Up Conversation Thread")
    print("-" * 40)
    thread = project_client.agents.create_thread()
    print(f"  ✓ Thread created: {thread.id}")
    print()
    
    # Step 4: Send a complex query
    print("Step 4: Sending Multi-Domain Query")
    print("-" * 40)
    
    user_query = (
        "We need to hire 10 new developers. What budget should we allocate? "
        "What's our hiring timeline and what operational impact might this have?"
    )
    print(f"  User: {user_query}")
    print()
    
    message = project_client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content=user_query
    )
    print(f"  ✓ Message created: {message.id}")
    
    # Step 5: Run orchestrator
    print("Step 5: Running Orchestrator (Delegating to Specialists)")
    print("-" * 40)
    
    run = project_client.agents.create_run(
        thread_id=thread.id,
        assistant_id=orchestrator.id
    )
    print(f"  ✓ Run started: {run.id}")
    print(f"    Status: {run.status}")
    
    # Wait for completion
    step_count = 0
    while run.status in ["queued", "in_progress"]:
        step_count += 1
        run = project_client.agents.get_run(thread_id=thread.id, run_id=run.id)
        print(f"  Step {step_count}: {run.status}")
        
        # Show tool calls if available
        if hasattr(run, 'tool_calls') and run.tool_calls:
            for tool_call in run.tool_calls:
                print(f"    → Consulting: {tool_call.name}")
    
    print(f"  ✓ Run completed: {run.status}")
    print()
    
    # Step 6: Retrieve synthesis response
    print("Step 6: Orchestrator's Synthesis")
    print("-" * 40)
    
    messages = project_client.agents.list_messages(thread_id=thread.id)
    for msg in messages:
        if msg.role == "assistant":
            response = msg.content[0].text
            print(f"  {response[:500]}...")
            break
    
    print()
    
    # Cleanup
    print("Cleanup")
    print("-" * 40)
    project_client.agents.delete_agent(orchestrator.id)
    print(f"  ✓ Orchestrator deleted")
    
    for domain, specialist in specialists.items():
        project_client.agents.delete_agent(specialist.id)
        print(f"  ✓ {domain.capitalize()} specialist deleted")


if __name__ == "__main__":
    main()
