---
title: "Microsoft Foundry SDK: Part 7 – Guardrails for agents"
excerpt: "Apply and test model-level and agent-level Responsible AI policies in Microsoft Foundry, including blocking and annotation behavior."
slug: microsoft-foundry/part7-guardrails
artifactPath: "microsoft-foundry/part7-guardrails"
tags: ["azure", "ai-foundry", "sdk", "python", "agents", "guardrails", "responsible-ai"]
series: {"slug":"microsoft-foundry","title":"Microsoft Foundry","part":7}
publishAt: null
---
# Part 7 – Guardrails: model and agent safety policies

Guardrails are enforced policies, not a local dictionary printed next to a response. In Foundry, model-level safety settings and agent-level instructions/tools work together: the model can return safety annotations or block a request, while the agent configuration limits what the agent is allowed to do.

## Prerequisites and boundaries

Configure Azure AI Content Safety/model safety settings and the agent's instructions/tool permissions in the Foundry project or the model deployment used by your project. Names and SDK fields vary by model and preview API. The examples use the stable response shape and show where to inspect annotations; they do not claim that a Python boolean applies a server-side policy.

```bash
pip install "azure-ai-projects>=2.4.0" azure-identity openai python-dotenv
```

## Model-level policies: block or annotate

Model-level policies address categories such as hate, violence, sexual content, and self-harm. Depending on the configured policy, a request may be blocked, or the response may include safety annotations. `model_safety_probe.py` calls a deployed agent and reports the observed result without fabricating an enforcement decision. Confirm the authoritative decision and thresholds in the Foundry portal and deployment configuration.

## Agent-level policies

Agent-level guardrails can bind a Foundry RAI policy to the agent definition. They can also include narrow instructions, tool allow-lists, confirmation steps for consequential actions, input validation, and a least-privilege project identity. `agent_policy.py` creates an agent version with `RaiConfig`; the policy is enforced by Foundry, not by a local Python boolean. This remains complementary to model safety filtering and Content Safety.

Never rely on instructions alone for high-impact actions. Put authorization and validation in the tool/service boundary, log policy outcomes, and fail closed when a required safety signal is missing.

## Test the policy

`guardrail_tests.py` provides a small table of safe, borderline, and disallowed prompts. It invokes the configured endpoint and records whether the service returned a response, a refusal/error, or safety annotations. It does not classify text with a local keyword list and call that a Foundry guardrail. Expand the cases with your safety team and assert the policy behavior you actually configured.

## Run the sample

```bash
python code/agent_policy.py
python code/model_safety_probe.py
python code/guardrail_tests.py
```

Required environment variables are `AZURE_AI_PROJECT_ENDPOINT`, `MODEL_DEPLOYMENT`, `FOUNDRY_RAI_POLICY_ID`, and (for probes) `FOUNDRY_AGENT_NAME`. Use non-sensitive test prompts, avoid logging message content, and review blocked/annotated samples under your organization's RAI process.

Next: [Part 8 – Multi-agent orchestration](/blog/microsoft-foundry/part8-multi-agent-orchestration), [Part 9 – Deploying hosted agents](/blog/microsoft-foundry/part9-deploying-hosted-agents), and [Part 10 – From notebook to production](/blog/microsoft-foundry/part10-from-notebook-to-production).

---

## Full sample code

- [agent_policy.py](code/agent_policy.py)
- [model_safety_probe.py](code/model_safety_probe.py)
- [guardrail_tests.py](code/guardrail_tests.py)
