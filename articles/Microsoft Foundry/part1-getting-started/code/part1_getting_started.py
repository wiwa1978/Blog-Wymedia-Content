"""
Microsoft Foundry SDK - Part 1: Getting Started
Complete example demonstrating basic agent creation and invocation.

This script shows:
1. Creating a virtual environment and installing dependencies
2. Setting up Foundry project client with authentication
3. Creating a simple prompt-based agent
4. Invoking the agent and streaming responses
"""

import os
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential

def main():
    # Initialize the Foundry project client
    # Authentication uses DefaultAzureCredential (checks env vars, managed identity, etc.)
    project_client = AIProjectClient.from_config(
        credential=DefaultAzureCredential()
    )
    
    print(f"✓ Connected to project: {project_client.project_name}")
    print(f"  Resource Group: {project_client.resource_group_name}")
    print(f"  Endpoint: {project_client.endpoint}")
    print()
    
    # Define a simple prompt-based agent
    agent_definition = PromptAgentDefinition(
        name="getting-started-agent",
        instructions="You are a helpful AI assistant. Answer questions concisely."
    )
    
    print("Creating agent with definition:")
    print(f"  Name: {agent_definition.name}")
    print(f"  Model: gpt-4o-mini")
    print()
    
    # Create the agent (stored in the Foundry project)
    agent = project_client.agents.create_agent(
        agent_definition=agent_definition,
        model="gpt-4o-mini"
    )
    
    print(f"✓ Agent created successfully!")
    print(f"  Agent ID: {agent.id}")
    print(f"  Name: {agent.name}")
    print()
    
    # Create a thread (conversation session)
    thread = project_client.agents.create_thread()
    print(f"✓ Thread created: {thread.id}")
    print()
    
    # Send a message to the agent
    user_message = "What is the capital of France?"
    print(f"User: {user_message}")
    
    message = project_client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content=user_message
    )
    print(f"✓ Message sent to thread")
    print()
    
    # Run the agent (process the message)
    run = project_client.agents.create_run(thread_id=thread.id, assistant_id=agent.id)
    print(f"✓ Agent run created: {run.id}")
    print(f"  Status: {run.status}")
    print()
    
    # Wait for the run to complete
    print("Waiting for agent to process...")
    while run.status in ["queued", "in_progress"]:
        run = project_client.agents.get_run(thread_id=thread.id, run_id=run.id)
        print(f"  Status: {run.status}")
    
    print(f"✓ Run completed: {run.status}")
    print()
    
    # Retrieve the agent's response
    messages = project_client.agents.list_messages(thread_id=thread.id)
    
    print("Agent Response:")
    for msg in messages:
        if msg.role == "assistant":
            print(f"  {msg.content[0].text}")
            break
    
    print()
    
    # Cleanup: Delete the agent
    project_client.agents.delete_agent(agent.id)
    print(f"✓ Agent deleted: {agent.id}")


if __name__ == "__main__":
    main()
