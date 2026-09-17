"""Part 2.3 - Define a custom function tool and execute it locally."""

import json

from azure.ai.projects.models import FunctionTool, PromptAgentDefinition, Tool
from openai.types.responses.response_input_param import (
    FunctionCallOutput,
    ResponseInputParam,
)

from _common import MODEL_DEPLOYMENT, agent_reference, create_clients


def get_horoscope(sign: str) -> str:
    """Generate a horoscope for the given astrological sign."""
    return f"{sign}: Next Tuesday you will befriend a baby otter."


project, openai = create_clients()
func_tool = FunctionTool(
    name="get_horoscope",
    parameters={
        "type": "object",
        "properties": {
            "sign": {
                "type": "string",
                "description": "An astrological sign like Taurus or Aquarius",
            },
        },
        "required": ["sign"],
        "additionalProperties": False,
    },
    description="Get today's horoscope for an astrological sign.",
    strict=True,
)

tools: list[Tool] = [func_tool]
agent = project.agents.create_version(
    agent_name="FunctionToolAgent",
    definition=PromptAgentDefinition(
        model=MODEL_DEPLOYMENT,
        instructions="You are a helpful assistant that can use function tools.",
        tools=tools,
    ),
)
print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")

conversation = openai.conversations.create()
response = openai.responses.create(
    input="What is my horoscope? I am an Aquarius.",
    conversation=conversation.id,
    extra_body=agent_reference(agent.name),
)

input_list: ResponseInputParam = []
for item in response.output:
    if item.type == "function_call" and item.name == "get_horoscope":
        result = get_horoscope(**json.loads(item.arguments))
        print(f"Executed local function -> {result}")
        input_list.append(
            FunctionCallOutput(
                type="function_call_output",
                call_id=item.call_id,
                output=json.dumps({"horoscope": result}),
            )
        )

response = openai.responses.create(
    input=input_list,
    conversation=conversation.id,
    extra_body=agent_reference(agent.name),
)
print(f"Final answer: {response.output_text}")

project.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
