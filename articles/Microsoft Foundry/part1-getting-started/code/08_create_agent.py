"""
Step 9 - Create your first agent.

An agent packages a model + instructions into a reusable, versioned
identity so you don't have to repeat the system prompt every call.
"""
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

load_dotenv()
PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "your_project_endpoint")
MODEL_DEPLOYMENT = os.getenv("MODEL_DEPLOYMENT", "gpt-5.1-mini")
AGENT_NAME = "MyFirstAgent"

project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())

agent = project.agents.create_version(
    agent_name=AGENT_NAME,
    definition=PromptAgentDefinition(
        model=MODEL_DEPLOYMENT,
        instructions="You are a helpful assistant that answers general questions.",
    ),
)

print("✓ Agent created")
print(f"  Name:    {agent.name}")
print(f"  ID:      {agent.id}")
print(f"  Version: {agent.version}")
