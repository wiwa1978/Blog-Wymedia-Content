---
title: "Microsoft Agent Framework - Part 3: Orchestrating Multiple Agents"
excerpt: "In [Part 1](../part1-getting-started/microsoft-agent-framework-part1-getting-started.md) we built a single agent with a tool, and [Part 2](../part2-tools-and-structured-data/microsoft-agent-framework-part2-tools-and-stru…"
slug: microsoft-agent-framework/part3-orchestration
artifactPath: "Microsoft Agent Framework/part3-orchestration"
tags: ["microsoft-agent-framework", "python", "ai-agents", "multi-agent", "orchestration", "workflows"]
series: null
publishAt: "2026-07-29T09:34:00.000Z"
---
# Microsoft Agent Framework, Part 3: Orchestrating Multiple Agents

In [Part 1](/blog/microsoft-agent-framework/part1-getting-started) we built a single agent with a tool, and [Part 2](/blog/microsoft-agent-framework/part2-tools-and-structured-data) made its tool and data contracts more useful. This post introduces the **workflow engine**: a graph-based way to connect specialized agents so they collaborate instead of each trying to do everything.

This post builds two multi-agent patterns step by step:

1. **Sequential orchestration** — a pipeline where each agent builds on the previous agent's output (e.g. writer → reviewer).
2. **Concurrent orchestration** — multiple agents tackle the same input in parallel and their answers are aggregated (e.g. three specialists reviewing the same text from different angles).

We reuse the same virtual environment and `OpenAIChatClient` setup from Part 1 — no new Azure resources required.

## Prerequisites

- Completed Part 1 (virtual environment activated, `agent-framework-openai` installed, `.env` with `OPENAI_API_KEY` / `OPENAI_CHAT_MODEL`)
- No extra packages needed — the orchestration builders ship inside the core `agent_framework` package

## Step 1 — Recap: two agents, no orchestration yet

Before wiring agents together, let's just create two of them so we can see their individual "identities" printed out.

```python
# agents.py
from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient

client = OpenAIChatClient()

writer = Agent(
    client=client,
    name="writer",
    instructions=(
        "You are a concise marketing copywriter. Given a product description, "
        "write one punchy, single-sentence tagline."
    ),
)

reviewer = Agent(
    client=client,
    name="reviewer",
    instructions=(
        "You are a critical marketing reviewer. Read the previous message and give "
        "brief, actionable feedback in 1-2 sentences."
    ),
)

print(f"Created agents: {[writer.name, reviewer.name]}")
```

```text
Created agents: ['writer', 'reviewer']
```

Each agent only knows how to do *one* thing well. That specialization is the whole idea behind multi-agent design.

## Step 2 — Sequential orchestration: writer → reviewer

The `SequentialBuilder` chains agents into a pipeline. Each agent in the chain sees the **full conversation so far** (including earlier agents' replies) and appends its own response.

```python
# 01_sequential.py
import asyncio
from agent_framework import Agent, AgentResponse
from agent_framework.openai import OpenAIChatClient
from agent_framework.orchestrations import SequentialBuilder
from dotenv import load_dotenv

load_dotenv()


async def main() -> None:
    client = OpenAIChatClient()

    writer = Agent(
        client=client,
        name="writer",
        instructions=(
            "You are a concise marketing copywriter. Given a product description, "
            "write one punchy, single-sentence tagline."
        ),
    )
    reviewer = Agent(
        client=client,
        name="reviewer",
        instructions=(
            "You are a critical marketing reviewer. Read the previous message and give "
            "brief, actionable feedback in 1-2 sentences."
        ),
    )

    workflow = SequentialBuilder(participants=[writer, reviewer]).build()
    print(f"Built sequential pipeline: {[p.name for p in [writer, reviewer]]}")

    events = await workflow.run("A budget-friendly electric bike for daily commuters.")
    outputs = events.get_outputs()

    if outputs:
        final: AgentResponse = outputs[0]
        print("\n===== Full conversation =====")
        for msg in final.messages:
            name = msg.author_name or "assistant"
            print(f"[{name}] {msg.text}")


asyncio.run(main())
```

Run it:

```bash
python 01_sequential.py
```

```text
Built sequential pipeline: ['writer', 'reviewer']

===== Full conversation =====
[user] A budget-friendly electric bike for daily commuters.
[writer] "Ride further, spend less — the eBike built for your everyday commute."
[reviewer] Strong value message, but consider tightening it — dropping "the eBike built for"
would make it punchier while keeping the core benefit.
```

Notice the pipeline is entirely declarative: `SequentialBuilder(participants=[writer, reviewer]).build()`. Adding a third stage (e.g. a "polish" agent) is a one-line change.

## Step 3 — Concurrent orchestration: parallel specialists

Sometimes you don't want a pipeline — you want several agents to independently look at the **same** input and combine their perspectives. `ConcurrentBuilder` fans a single input out to multiple agents and aggregates their responses.

```python
# 02_concurrent.py
import asyncio
from agent_framework import Agent, AgentResponse
from agent_framework.openai import OpenAIChatClient
from agent_framework.orchestrations import ConcurrentBuilder
from dotenv import load_dotenv

load_dotenv()


async def main() -> None:
    client = OpenAIChatClient()

    clarity_reviewer = Agent(
        client=client,
        name="clarity_reviewer",
        instructions="Review the text for clarity only. Give one short bullet point of feedback.",
    )
    tone_reviewer = Agent(
        client=client,
        name="tone_reviewer",
        instructions="Review the text for tone only. Give one short bullet point of feedback.",
    )
    seo_reviewer = Agent(
        client=client,
        name="seo_reviewer",
        instructions="Review the text for SEO/keyword strength only. Give one short bullet point of feedback.",
    )

    reviewers = [clarity_reviewer, tone_reviewer, seo_reviewer]
    workflow = ConcurrentBuilder(participants=reviewers).build()
    print(f"Fan-out to {len(reviewers)} reviewers: {[r.name for r in reviewers]}")

    tagline = "Ride further, spend less — the eBike built for your everyday commute."
    events = await workflow.run(tagline)
    outputs = events.get_outputs()

    if outputs:
        final: AgentResponse = outputs[0]
        print(f"\n===== Feedback on: \"{tagline}\" =====")
        for msg in final.messages:
            name = msg.author_name or "assistant"
            print(f"[{name}] {msg.text}")


asyncio.run(main())
```

Run it:

```bash
python 02_concurrent.py
```

```text
Fan-out to 3 reviewers: ['clarity_reviewer', 'tone_reviewer', 'seo_reviewer']

===== Feedback on: "Ride further, spend less — the eBike built for your everyday commute." =====
[clarity_reviewer] - Clear and easy to understand at a glance; no changes needed.
[tone_reviewer] - Friendly and approachable tone; fits a budget-conscious commuter audience well.
[seo_reviewer] - Consider working in "electric bike" explicitly, since "eBike" alone may under-perform on search.
```

All three reviewers ran against the same input independently — the SEO reviewer's opinion didn't influence the tone reviewer's, which is exactly what you want for unbiased, parallel feedback.

## Step 4 — Combine both: pipeline with a concurrent review stage

Real workflows often mix patterns. Here, the writer drafts a tagline, then three specialists review it **concurrently**, and finally an editor consolidates their feedback into one recommendation.

```python
# 03_combined_workflow.py
import asyncio
from agent_framework import Agent, AgentResponse
from agent_framework.openai import OpenAIChatClient
from agent_framework.orchestrations import ConcurrentBuilder, SequentialBuilder
from dotenv import load_dotenv

load_dotenv()


async def main() -> None:
    client = OpenAIChatClient()

    writer = Agent(
        client=client,
        name="writer",
        instructions="Write one punchy, single-sentence marketing tagline for the given product.",
    )
    clarity_reviewer = Agent(
        client=client, name="clarity_reviewer",
        instructions="Review the tagline for clarity only. One short bullet point.",
    )
    tone_reviewer = Agent(
        client=client, name="tone_reviewer",
        instructions="Review the tagline for tone only. One short bullet point.",
    )
    seo_reviewer = Agent(
        client=client, name="seo_reviewer",
        instructions="Review the tagline for SEO strength only. One short bullet point.",
    )
    editor = Agent(
        client=client,
        name="editor",
        instructions=(
            "You are the final editor. Read the tagline and all reviewer feedback above, "
            "then produce one final, improved tagline plus a one-sentence justification."
        ),
    )

    # Stage 1: writer drafts, Stage 2: three reviewers run concurrently, Stage 3: editor finalizes.
    review_stage = ConcurrentBuilder(participants=[clarity_reviewer, tone_reviewer, seo_reviewer]).build()
    pipeline = SequentialBuilder(participants=[writer, review_stage, editor]).build()

    print("Pipeline: writer -> [clarity + tone + seo reviewers in parallel] -> editor")

    events = await pipeline.run("A budget-friendly electric bike for daily commuters.")
    outputs = events.get_outputs()

    if outputs:
        final: AgentResponse = outputs[0]
        print("\n===== Full workflow trace =====")
        for msg in final.messages:
            name = msg.author_name or "assistant"
            print(f"[{name}] {msg.text}")


asyncio.run(main())
```

```text
Pipeline: writer -> [clarity + tone + seo reviewers in parallel] -> editor

===== Full workflow trace =====
[user] A budget-friendly electric bike for daily commuters.
[writer] "Ride further, spend less — the eBike built for your everyday commute."
[clarity_reviewer] - Clear and easy to understand; no changes needed.
[tone_reviewer] - Friendly, budget-conscious tone that fits the audience well.
[seo_reviewer] - Spell out "electric bike" instead of "eBike" for better search visibility.
[editor] Final tagline: "Ride further, spend less — the electric bike built for your everyday
commute." Justification: keeps the friendly, value-driven tone while improving searchability
by spelling out "electric bike."
```

A `SequentialBuilder` can take another workflow (like the `review_stage` concurrent block) as one of its participants — that's how sequential and concurrent patterns compose into richer graphs.

## What to try next

1. **Handoff orchestration** — instead of a fixed pipeline, let agents dynamically decide which specialist should handle the next turn (useful for customer-support style routing).
2. **Group-chat orchestration** — let agents debate each other directly instead of processing in strict turns.
3. **Magentic orchestration** — an open-ended planner agent that dynamically assigns sub-tasks to specialist agents, useful for complex, non-linear problems.
4. **Human-in-the-loop** — pause the pipeline before a sensitive tool call (e.g. `DeployToProduction`) and require explicit approval before the workflow continues.
5. **Checkpoints** — persist workflow state so a long-running multi-agent job can resume after a crash or restart.



## Why this matters

Once you've built one good agent, the natural next question is "how do I get several good agents to work together without babysitting the hand-offs myself?" Agent Framework's orchestration builders (`SequentialBuilder`, `ConcurrentBuilder`, and friends) turn that coordination logic into a few declarative lines, while the underlying workflow engine — inherited from AutoGen's multi-agent research — handles the event streaming, state, and composition for you.
