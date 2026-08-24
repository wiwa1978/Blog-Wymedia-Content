---
title: "Microsoft Foundry SDK - Part 3 - Trust but verify: observability, evaluations, and guardrails"
excerpt: "Learn how to make Microsoft Foundry agents trustworthy with tracing, evaluations, and guardrails backed by practical Python examples."
slug: microsoft-foundry/part3-observability-evaluation-guardrails
artifactPath: "Microsoft Foundry/part3-observability-evaluation-guardrails"
tags: ["azure", "ai-foundry", "sdk", "python", "agents", "observability", "tracing", "evaluation", "guardrails", "responsible-ai"]
series: null
publishAt: "2026-07-06T18:01:00.000Z"
---
# Part 3 - Trust but verify: observability, evaluations, and guardrails in the Microsoft Foundry SDK

Parts [1](/blog/microsoft-foundry/part1-getting-started) and [2](/blog/microsoft-foundry/part2-tools-mcp-memory) of this series built agents and gave them capabilities — web search, file search, functions, MCP, toolboxes, memory. Shipping an agent to real users raises a different set of questions:

- **Where did this response come from?** Which model call, which tool, which step introduced the error or the latency spike?
- **Is it actually any good?** Does it complete tasks, stay grounded, avoid making things up?
- **Is it safe?** Can a user manipulate it into producing harmful content or leaking data?

Foundry Agent Service answers these with three connected pillars — **tracing**, **evaluation**, and **guardrails** — all backed by the same `azure-ai-projects` SDK you already know. This post walks through each, in increasing complexity, with runnable snippets that print what's happening.

## Prerequisites

```bash
pip install "azure-ai-projects>=2.4.0" azure-identity opentelemetry-sdk azure-core-tracing-opentelemetry azure-monitor-opentelemetry
```

```python
import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

PROJECT_ENDPOINT = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
MODEL_DEPLOYMENT = os.environ["FOUNDRY_MODEL_NAME"]

project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=DefaultAzureCredential())
openai = project.get_openai_client()
print(f"Connected to project: {PROJECT_ENDPOINT}")
```

> Foundry already captures **server-side traces** for every Prompt agent, Hosted agent, and workflow automatically — no code required, visible under **Observability > Traces** in the portal for the last 90 days. The tracing snippets below add **client-side** traces from your own application code on top of that, and are what you need if you want traces in your own Application Insights, Datadog, Grafana, or console.

## 1. Trace locally with the console exporter

Before shipping anything to the cloud, see traces on your own machine. This is the fastest way to understand what a single agent call actually does under the hood.

```python
import os

os.environ["AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING"] = "true"  # opt in — tracing is preview

from azure.ai.projects.telemetry import AIProjectInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

tracer_provider = TracerProvider()
tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(tracer_provider)

# Turn on instrumentation for azure-ai-projects / OpenAI calls
AIProjectInstrumentor().instrument()

agent = project.agents.create_version(
    agent_name="TracedAgent",
    definition=PromptAgentDefinition(model=MODEL_DEPLOYMENT, instructions="You are a helpful assistant."),
)
print(f"Agent created (id: {agent.id}, name: {agent.name})")

conversation = openai.conversations.create()
response = openai.responses.create(
    conversation=conversation.id,
    input="What is the largest city in France?",
    extra_body={"agent_reference": {"name": agent.name, "id": agent.id, "type": "agent_reference"}},
)
print(f"Response: {response.output_text}")
# Spans for the request, the model call, and any tool calls print to stdout as they complete
```

**What just happened:** every model call and tool invocation is now wrapped in an OpenTelemetry span, printed straight to your console. No Azure resource needed yet — this is purely local.

## 2. Export traces to Azure Monitor Application Insights

Once you're ready to see traces in the Foundry portal itself (and keep them for 90 days), point the exporter at your project's Application Insights resource instead of the console.

```python
import os

os.environ["AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING"] = "true"

from opentelemetry import trace
from azure.monitor.opentelemetry import configure_azure_monitor

with DefaultAzureCredential() as credential, AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential) as project:
    # The project already knows which App Insights resource it's connected to
    connection_string = project.telemetry.get_application_insights_connection_string()
    configure_azure_monitor(connection_string=connection_string)
    print("Azure Monitor exporter configured")

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("agent-tracing-scenario"):
        with project.get_openai_client() as openai:
            agent = project.agents.create_version(
                agent_name="MonitoredAgent",
                definition=PromptAgentDefinition(model=MODEL_DEPLOYMENT, instructions="You are a helpful assistant."),
            )
            print(f"Agent created (id: {agent.id}, name: {agent.name})")

            conversation = openai.conversations.create()
            response = openai.responses.create(
                conversation=conversation.id,
                # Passing both name and id lets the Foundry portal correlate this trace to the agent
                extra_body={"agent_reference": {"name": agent.name, "id": agent.id, "type": "agent_reference"}},
                input="What is the largest city in France?",
            )
            print(f"Response: {response.output_text}")

            openai.conversations.delete(conversation_id=conversation.id)
            project.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
```

**What just happened:** traces now flow to the same Application Insights resource your Foundry project uses, and show up in the portal's **Traces** view within a couple of minutes. `agent_reference` is what links a trace back to a specific agent.

## 3. Capture message content (development only)

By default, traces record structure (spans, durations, token counts) but not the actual message text — useful for privacy, unhelpful for debugging. Turn on content recording only in development.

```python
import os

# Caution: captures user messages, tool arguments, and model outputs. Dev only.
os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "true"
```

You can also trace your own custom functions with the same tracer, so a local function call shows up as a span alongside the model and tool calls:

```python
tracer = trace.get_tracer(__name__)

def enrich_customer_data(customer_id: str) -> dict:
    with tracer.start_as_current_span("enrich_customer_data") as span:
        span.set_attribute("customer_id", customer_id)
        result = {"customer_id": customer_id, "tier": "gold"}
        span.set_attribute("tier", result["tier"])
        return result

print(enrich_customer_data("cust_123"))
```

**What just happened:** you now have full input/output visibility for debugging, plus your own business logic appearing in the same trace tree as the model and tool calls — all from the same tracer instance.

## 4. Run your first evaluation

Tracing tells you *what happened*. Evaluation tells you *how good it was*. Start with a **rubric evaluator** — a set of weighted scoring dimensions an LLM judge applies consistently to every response — generated automatically from your agent's own definition.

```python
import time
import uuid
from azure.ai.projects.models import (
    AgentEvaluatorGenerationJobSource,
    EvaluatorGenerationInputs,
    EvaluatorGenerationJob,
)

AGENT_NAME = agent.name  # reuse an agent from part 1 or 2

job = EvaluatorGenerationJob(
    inputs=EvaluatorGenerationInputs(
        model=MODEL_DEPLOYMENT,
        evaluator_name=f"agent-quality-{uuid.uuid4().hex[:8]}",
        evaluator_display_name="Agent Quality",
        sources=[AgentEvaluatorGenerationJobSource(agent_name=AGENT_NAME)],
    ),
)
poller = project.beta.evaluators.begin_create_generation_job(job=job)

while not poller.done():
    print(f"  status: {poller.status()}")
    time.sleep(10)

rubric_evaluator = poller.result()
print(f"Generated rubric: {rubric_evaluator.name} v{rubric_evaluator.version}")
for dim in rubric_evaluator.definition.dimensions:
    print(f"  - {dim.id} (weight {dim.weight}): {dim.description}")
```

Now build a tiny test dataset and pair the generated rubric with a couple of built-in evaluators (a safety metric and a quality metric):

```python
# test-queries.jsonl
# {"query": "What's the weather in Seattle?"}
# {"query": "Book a flight to Paris"}
# {"query": "Tell me a joke"}

dataset = project.datasets.upload_file(name="agent-test-queries", version="1", file_path="./test-queries.jsonl")
print(f"Uploaded dataset: {dataset.name}, version: {dataset.version}")

from azure.ai.projects.models import TestingCriterionAzureAIEvaluator

testing_criteria = [
    TestingCriterionAzureAIEvaluator(
        type="azure_ai_evaluator",
        name="Agent Quality",
        evaluator_name=rubric_evaluator.name,
        initialization_parameters={"deployment_name": MODEL_DEPLOYMENT},
        data_mapping={"query": "{{item.query}}", "response": "{{sample.output_items}}"},
    ),
    TestingCriterionAzureAIEvaluator(
        type="azure_ai_evaluator",
        name="Violence",
        evaluator_name="builtin.violence",
        data_mapping={"query": "{{item.query}}", "response": "{{sample.output_text}}"},
    ),
    TestingCriterionAzureAIEvaluator(
        type="azure_ai_evaluator",
        name="Coherence",
        evaluator_name="builtin.coherence",
        initialization_parameters={"deployment_name": MODEL_DEPLOYMENT},
        data_mapping={"query": "{{item.query}}", "response": "{{sample.output_text}}"},
    ),
]
```

Create the evaluation container, then a run that actually sends your dataset to the agent and scores the results:

```python
from openai.types.eval_create_params import DataSourceConfigCustom

data_source_config = DataSourceConfigCustom(
    type="custom",
    item_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    include_sample_schema=True,
)

evaluation = openai.evals.create(
    name="Agent Quality Evaluation",
    data_source_config=data_source_config,
    testing_criteria=testing_criteria,
)
print(f"Evaluation created: {evaluation.id}")

eval_run = openai.evals.runs.create(
    eval_id=evaluation.id,
    name="Agent Evaluation Run",
    data_source={
        "type": "azure_ai_target_completions",
        "source": {"type": "file_id", "id": dataset.id},
        "input_messages": {
            "type": "template",
            "template": [{"type": "message", "role": "user", "content": {"type": "input_text", "text": "{{item.query}}"}}],
        },
        "target": {"type": "azure_ai_agent", "name": AGENT_NAME, "version": "1"},
    },
)
print(f"Evaluation run started: {eval_run.id}")
```

Finally, poll for the result and print a summary:

```python
import time

while True:
    run = openai.evals.runs.retrieve(run_id=eval_run.id, eval_id=evaluation.id)
    if run.status in ["completed", "failed"]:
        break
    time.sleep(5)

print(f"Status: {run.status}")
print(f"Report URL: {run.report_url}")
```

**What just happened:** the service sent every row of your test dataset to the agent, captured the responses (including tool calls), and scored each one against your rubric plus the built-in Violence and Coherence evaluators. Open `report_url` in a browser to see pass/fail counts, per-dimension scores, and the judge's reasoning for every row — right in the Foundry portal.

## 5. Turn on continuous evaluation for live traffic

A one-off evaluation run is a snapshot. **Continuous evaluation** samples real production traffic automatically and scores it as it happens, so you catch regressions without re-running anything manually.

```python
from azure.ai.projects.models import (
    EvaluationRule,
    ContinuousEvaluationRuleAction,
    EvaluationRuleFilter,
    EvaluationRuleEventType,
)

data_source_config = {"type": "azure_ai_source", "scenario": "responses"}
testing_criteria = [
    {"type": "azure_ai_evaluator", "name": "violence_detection", "evaluator_name": "builtin.violence"},
]

eval_object = openai.evals.create(
    name="Continuous Evaluation",
    data_source_config=data_source_config,
    testing_criteria=testing_criteria,
)
print(f"Continuous evaluation created (id: {eval_object.id}, name: {eval_object.name})")

# Foundry then samples a percentage of live requests to this agent and scores them automatically —
# results and trends surface in Observability > Monitor, connected back to the original traces.
```

**What just happened:** rather than you triggering evaluations, Foundry now samples live agent traffic on an ongoing basis and reports quality/safety trends in the **Monitor** dashboard — with every scored interaction linked back to its full trace for root-cause debugging.

## 6. Add a guardrail to block unsafe content

Tracing and evaluation tell you about quality after the fact. **Guardrails** (Responsible AI / RAI policies) intervene *before* a response reaches your user — screening the prompt going in, and the tool calls, tool responses, and final output coming out.

A guardrail is a named collection of **controls**: which risk to detect (hate, violence, self-harm, sexual, prompt injection, protected material, PII, task adherence...), which intervention point to scan (user input, tool call, tool response, output), and what to do about it (annotate, or annotate and block).

Once you've created a guardrail (RAI policy) in the Foundry portal or via the management API, reference its full ARM resource ID from your agent definition:

```python
from azure.ai.projects.models import PromptAgentDefinition, RaiConfig

RAI_POLICY_ID = (
    "/subscriptions/<subscription-id>/resourceGroups/<resource-group>"
    "/providers/Microsoft.CognitiveServices/accounts/<account>"
    "/raiPolicies/<policy-name>"
)

agent = project.agents.create_version(
    agent_name="GuardedAgent",
    definition=PromptAgentDefinition(
        model=MODEL_DEPLOYMENT,
        instructions="You are a helpful customer support assistant.",
        rai_config=RaiConfig(rai_policy_name=RAI_POLICY_ID),
    ),
)
print(f"Agent created (id: {agent.id}, name: {agent.name}) with guardrail: {RAI_POLICY_ID}")

# Confirm the policy stuck
fetched = project.agents.get_version(agent_name=agent.name, agent_version=agent.version)
print(f"Applied RAI policy: {fetched.definition.rai_config.rai_policy_name}")
```

**What just happened:** every prompt this agent receives and every response it produces is now screened against your organization's policy — independent of whatever guardrail is set on the underlying model deployment. If you omit `rai_config` entirely, the agent falls back to its model deployment's guardrail; if you set `rai_config` but no policy name, it uses `Microsoft.DefaultV2`.

> Guardrails only support **annotate and block** for agents (not "annotate only"), and processing adds roughly 50–100ms of latency per intervention point — start with the risks that matter most for your scenario rather than enabling everything at once.

## Putting it together

A production-ready agent combines all three: guardrails to prevent unsafe interactions, tracing to debug what happened, and evaluation to keep proving it's still good.

```python
os.environ["AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING"] = "true"

from azure.monitor.opentelemetry import configure_azure_monitor
from azure.ai.projects.telemetry import AIProjectInstrumentor
from azure.ai.projects.models import PromptAgentDefinition, RaiConfig

connection_string = project.telemetry.get_application_insights_connection_string()
configure_azure_monitor(connection_string=connection_string)
AIProjectInstrumentor().instrument()

production_agent = project.agents.create_version(
    agent_name="ProductionAgent",
    definition=PromptAgentDefinition(
        model=MODEL_DEPLOYMENT,
        instructions="You are a helpful customer support assistant.",
        rai_config=RaiConfig(rai_policy_name=RAI_POLICY_ID),
    ),
)
print(f"Production agent created (id: {production_agent.id}, version: {production_agent.version})")
print("Traced: yes | Guardrail applied: yes | Ready for continuous evaluation: yes")
```

## What to try next

- Add `initialization_parameters` and custom `data_mapping` to score tool-call accuracy or task completion specifically — see the Agent evaluators reference.
- Convert real production traces into an evaluation dataset instead of hand-writing test queries, so your evaluations reflect actual usage.
- Wire evaluation into CI/CD as a quality gate (for example with GitHub Actions) so a regression blocks a deployment automatically.
- Explore network egress controls on guardrails for Hosted agents — restricting which external destinations an agent can reach, not just what content it can produce.
- Use the AI red teaming agent to simulate adversarial attacks against your agent before it ever reaches production.

## Closing note

Tools make an agent capable; tracing, evaluation, and guardrails make it **trustworthy**. All three plug into the exact same `AIProjectClient` and `PromptAgentDefinition` you've been using since part 1 — tracing wraps your calls in spans, evaluation scores your agent's outputs against criteria you define, and guardrails intercept unsafe input or output before it matters. Start with console tracing and a single rubric evaluator locally, then layer in Application Insights, continuous evaluation, and a guardrail policy as you move toward production.

---

## Full Sample Code

The complete working example for this post is available on GitHub:

**[part3_observability_evaluation_guardrails.py](code/part3_observability_evaluation_guardrails.py)**

Run it locally:
```bash
python part3_observability_evaluation_guardrails.py
```

---

*Sources: [Microsoft Foundry Observability](https://learn.microsoft.com/azure/foundry/concepts/observability), [Agent Evaluation](https://learn.microsoft.com/azure/foundry/how-to/agents/evaluation), [Guardrails in AI Foundry](https://learn.microsoft.com/azure/foundry/concepts/guardrails), [Azure Monitor OpenTelemetry](https://learn.microsoft.com/azure/azure-monitor/app/opentelemetry-enable), [AI Safety and Responsible AI](https://learn.microsoft.com/azure/foundry/concepts/responsible-ai).*
