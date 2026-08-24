---
title: "Microsoft Agent Framework, Part 2: Multiple Tools and Structured Data"
excerpt: "In [Part 1](../part1-getting-started/microsoft-agent-framework-part1-getting-started.md) we created a single agent and gave it one tool. This post makes that agent useful in an application: it can choose between several…"
slug: microsoft-agent-framework/part2-tools-and-structured-data
artifactPath: "Microsoft Agent Framework/part2-tools-and-structured-data"
tags: ["microsoft-agent-framework", "python", "ai-agents", "tools", "structured-output"]
series: null
publishAt: "2026-07-25T18:57:00.000Z"
---
# Microsoft Agent Framework, Part 2: Multiple Tools and Structured Data

In [Part 1](../part1-getting-started/microsoft-agent-framework-part1-getting-started.md) we created a single agent and gave it one tool. This post makes that agent useful in an application: it can choose between several tools, accept validated structured input, and return a typed result that the rest of the application can trust.

The example is an **Azure solution-planning assistant**. It answers a request by selecting from a service catalog, checking regional availability, and estimating a rough monthly cost. The numbers are deliberately mock data; the design is the important part.

## What makes a good tool?

A tool is an application capability, not just a prompt shortcut. Keep its contract narrow, describe its parameters clearly, and make side effects explicit. Read-only tools are a good starting point. Tools that create, delete, deploy, or send something should have an application-level approval step rather than relying on the model alone.

## Define typed inputs

Use Pydantic models when a request contains more than one related value. This gives the model and your application the same contract.

```python
from pydantic import BaseModel, Field


class SolutionRequest(BaseModel):
    workload: str = Field(description="The workload the customer wants to run.")
    region: str = Field(description="The Azure region where it should run.")
    monthly_budget_usd: float = Field(gt=0, description="Maximum monthly budget in US dollars.")
```

Invalid values should be rejected before they reach a tool or a pricing calculation. Validation is not a replacement for authorization or business rules, but it prevents a large class of avoidable failures.

## Give the agent multiple tools

```python
from typing import Annotated
from pydantic import Field


def search_services(
    workload: Annotated[str, Field(description="Workload category, such as API or analytics.")],
) -> str:
    """Return candidate Azure services for a workload."""
    catalog = {
        "api": "Azure Container Apps, Azure App Service, or Azure Kubernetes Service",
        "analytics": "Microsoft Fabric, Azure Databricks, or Azure Synapse Analytics",
    }
    return catalog.get(workload.lower(), "No exact match; ask for more workload detail.")


def check_region_availability(
    service: Annotated[str, Field(description="Azure service name.")],
    region: Annotated[str, Field(description="Azure region name.")],
) -> str:
    """Check whether a service is available in a region."""
    return f"{service} is available in {region} for this example."


def estimate_monthly_cost(
    service: Annotated[str, Field(description="Azure service name.")],
    budget_usd: Annotated[float, Field(gt=0, description="Monthly budget in US dollars.")],
) -> str:
    """Return a rough estimate for an initial discussion."""
    return f"A small {service} deployment is estimated at ${budget_usd * 0.7:,.0f}/month."
```

Register all three functions on the same agent:

```python
from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient

agent = Agent(
    client=OpenAIChatClient(),
    name="solution_planner",
    instructions=(
        "You help plan Azure solutions. Use the service catalog first, then check "
        "availability and cost when the request contains enough information. "
        "Never claim that mock estimates are quotes."
    ),
    tools=[search_services, check_region_availability, estimate_monthly_cost],
)
```

The model chooses tools based on their names, descriptions, parameter descriptions, and the conversation. Your application remains responsible for validating the request and enforcing permissions.

## Return structured output

Free-form text is useful for a chat UI, but application code should not need to parse prose. Define the result your UI or API expects:

```python
class SolutionRecommendation(BaseModel):
    recommended_service: str
    region: str
    estimated_monthly_cost_usd: float = Field(ge=0)
    assumptions: list[str]
    risks: list[str]
```

Use the framework's structured-output support for the installed SDK version and validate the result before displaying or storing it. If validation fails, treat that as an application error to handle explicitly—not as a successful answer.

## A practical design rule

Use tools to obtain facts or perform controlled actions. Use structured output to communicate the result. Keep the natural-language answer as a presentation layer around those typed contracts.

## What to try next

1. Replace the mock catalog with a controlled internal service catalog.
2. Add an approval boundary before a tool that creates an Azure resource.
3. Add a second output model for rejected requests and missing information.
4. Pass the validated recommendation into the workflow introduced in Part 3.
