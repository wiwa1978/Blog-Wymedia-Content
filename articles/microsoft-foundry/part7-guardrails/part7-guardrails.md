---
title: "Compare agents with and without guardrails"
excerpt: "Create two Microsoft Foundry agents from the same support scenario, one without an RAI guardrail and one with a hosted-agent guardrail, then compare their behavior in the playground."
slug: microsoft-foundry/part7-guardrails
artifactPath: "microsoft-foundry/part7-guardrails"
tags: ["azure", "ai-foundry", "sdk", "python", "agents", "guardrails", "responsible-ai"]
series: {"slug":"microsoft-foundry","title":"Microsoft Foundry","part":7}
publishAt: "2026-08-01T13:59:00.000Z"
---
# Part 7 - Compare a Foundry agent with and without guardrails

The easiest way to understand guardrails is not to start with a large application architecture. It is to create two agents, open them in the Foundry playground, and send the same prompts to both:

1. A **baseline agent** with no hosted-agent RAI guardrail.
2. A **guarded agent** with a Foundry RAI policy attached through `RaiConfig`.

That is what this part does. The Python code creates both agents from the same support scenario so you can compare the behavior directly in Foundry, just like you would when testing in the playground.

## Scenario

The sample uses a small Contoso Audio support assistant. It answers questions about this return policy:

```text
Contoso Audio return policy:
- Standard returns are accepted within 30 days of delivery when the item is unused.
- Damaged or defective items must be reported within 14 days of delivery.
- Support can provide a prepaid return label after basic verification.
- Refunds are issued only after the returned item is received and inspected.
- Agents must not reveal private account, address, payment, or order details.
- Agents must not issue refunds, cancel orders, or change account data directly.
- Questions outside the policy should be answered with a limitation and a support handoff.
```

The baseline agent receives a simple instruction:

```text
Answer from the policy below. Be concise and helpful.
```

The guarded agent receives stricter instructions and a Foundry RAI policy. The difference is intentional: when you test in the playground, you should see both the effect of clearer agent instructions and the effect of the hosted-agent guardrail.

This is still a demo. In a production app you would also add authorization checks around tools and business actions, but that is not the goal of this article. Here the goal is simply: **what changes when I add a Foundry guardrail to the agent?**

## Prerequisites

Install the dependencies:

```bash
pip install -r code/requirements.txt
```

Create a `.env` file:

```bash
copy code\.env.example code\.env
```

Fill in:

```dotenv
AZURE_AI_PROJECT_ENDPOINT=https://<your-ai-resource>.services.ai.azure.com/api/projects/<your-project>
MODEL_DEPLOYMENT=gpt-4.1-mini
BASELINE_AGENT_NAME=support-agent-no-guardrail
GUARDED_AGENT_NAME=support-agent-with-guardrail
```

For the guarded agent, set `FOUNDRY_RAI_POLICY_NAME` to the full ARM resource ID of your Foundry RAI policy:

```dotenv
FOUNDRY_RAI_POLICY_NAME=/subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.CognitiveServices/accounts/<ai-account>/raiPolicies/<policy-name>
```

If you leave `FOUNDRY_RAI_POLICY_NAME` empty, the sample uses `Microsoft.DefaultV2`.

> Use approved safety test prompts from your organization's RAI test plan. Do not invent unsafe prompts in logs or tutorials.

## 1. Create the two agents

Run:

```bash
python code/01_create_agents.py
```

This creates:

- `support-agent-no-guardrail`
- `support-agent-with-guardrail`

The implementation is in [`01_create_agents.py`](code/01_create_agents.py). The important part is that the baseline definition has no `rai_config`, while the guarded definition includes one:

```python
baseline_agent = project.agents.create_version(
    agent_name=settings.baseline_agent_name,
    definition=HostedAgentDefinition(
        model=settings.model_deployment,
        instructions=BASELINE_INSTRUCTIONS,
    ),
)

guarded_agent = project.agents.create_version(
    agent_name=settings.guarded_agent_name,
    definition=HostedAgentDefinition(
        model=settings.model_deployment,
        instructions=GUARDED_INSTRUCTIONS,
        rai_config=RaiConfig(rai_policy_name=rai_policy_name),
    ),
)
```

That is the core comparison.

## 2. Compare in the Foundry playground

Open the Foundry playground and select the baseline agent first.

Try a normal support prompt:

```text
Can I return unused headphones 20 days after delivery?
```

Then switch to the guarded agent and send the same prompt. Both agents should answer from the policy: standard returns are allowed within 30 days when the item is unused.

Now try prompts from your approved RAI test plan. The exact observed behavior depends on your model, deployment, RAI policy, and tenant configuration, but the comparison you are looking for is:

| Prompt type | Baseline agent | Guarded agent |
| --- | --- | --- |
| Normal support question | Should answer from the support policy | Should answer from the support policy |
| Private-data or consequential-action request | May rely mostly on instructions | Should be more likely to refuse or avoid unsafe handling |
| Approved RAI safety test prompt | May respond, refuse, or annotate depending on model defaults | Should follow the attached RAI policy behavior |

If the guarded agent behaves exactly like the baseline for prompts that should trigger your policy, verify the policy resource ID and confirm the policy is attached to the agent version you are testing. Do not treat successful agent creation as proof that the policy is working.

## 3. Compare from the command line

The playground is the clearest way to see the difference, but you can also send one prompt to both agents:

```bash
python code/02_compare_agents.py "Can I return unused headphones 20 days after delivery?"
```

or use the prompt from `.env`:

```bash
python code/02_compare_agents.py
```

The script prints the baseline answer and the guarded answer side by side.

For an approved safety prompt, set:

```dotenv
RAI_TEST_PROMPT=Use an approved RAI test prompt from your safety test plan here.
```

Then run:

```bash
python code/02_compare_agents.py "%RAI_TEST_PROMPT%"
```

On PowerShell, you can use:

```powershell
python code/02_compare_agents.py $env:RAI_TEST_PROMPT
```

## 4. What each file does

The sample intentionally stays small and sequential:

| File | Purpose |
| --- | --- |
| [.env.example](code/.env.example) | Required settings for the comparison. |
| [requirements.txt](code/requirements.txt) | Python dependencies. |
| [01_create_agents.py](code/01_create_agents.py) | Creates the baseline and guarded agents. Run this first. |
| [02_compare_agents.py](code/02_compare_agents.py) | Sends one prompt to both agents. Run this second. |

## What this proves

This example proves the basic Foundry workflow:

1. You can create a normal hosted agent.
2. You can create a second hosted agent with `RaiConfig`.
3. You can open both in the playground and compare behavior using the same prompts.
4. You can repeat the same comparison from Python.

It does not replace a full safety review, authorization layer, or production policy enforcement plan. It is a focused lab for understanding the before/after behavior of hosted-agent guardrails.

Next: [Part 8 - Multi-agent orchestration](/blog/microsoft-foundry/part8-multi-agent-orchestration), [Part 9 - Deploying hosted agents](/blog/microsoft-foundry/part9-deploying-hosted-agents), and [Part 10 - From notebook to production](/blog/microsoft-foundry/part10-from-notebook-to-production).

---

## Full sample code

- [.env.example](code/.env.example)
- [requirements.txt](code/requirements.txt)
- [01_create_agents.py](code/01_create_agents.py)
- [02_compare_agents.py](code/02_compare_agents.py)
