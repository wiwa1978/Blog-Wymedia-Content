"""Part 2.1 - Attach the built-in web search tool."""

from azure.ai.projects.models import (
    PromptAgentDefinition,
    WebSearchApproximateLocation,
    WebSearchTool,
)

from _common import MODEL_DEPLOYMENT, agent_reference, create_clients


project, openai = create_clients()
agent = project.agents.create_version(
    agent_name="WebSearchAgent",
    definition=PromptAgentDefinition(
        model=MODEL_DEPLOYMENT,
        instructions="You are a helpful assistant that can search the web.",
        tools=[
            WebSearchTool(
                user_location=WebSearchApproximateLocation(
                    country="BE",
                    city="Brussels",
                    region="Brussels",
                )
            )
        ],
    ),
    description="Agent for web search.",
)
print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")

response = openai.responses.create(
    tool_choice="required",
    input="What is today's date and the weather in Seattle?",
    extra_body=agent_reference(agent.name),
)
print(response.output_text)

for item in response.output:
    if item.type == "message":
        for content in item.content:
            for annotation in getattr(content, "annotations", []):
                if annotation.type == "url_citation":
                    print(f"Source: {annotation.url}")
