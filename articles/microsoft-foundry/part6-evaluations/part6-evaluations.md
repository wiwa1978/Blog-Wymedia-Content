---
title: "Evaluate agent quality"
excerpt: "Build Foundry evaluation datasets, use built-in and rubric evaluators, inspect evaluation runs, and plan continuous evaluation."
slug: microsoft-foundry/part6-evaluations
artifactPath: "microsoft-foundry/part6-evaluations"
tags: ["azure", "ai-foundry", "sdk", "python", "agents", "evaluation", "quality"]
series: {"slug":"microsoft-foundry","title":"Microsoft Foundry","part":6}
publishAt: null
---
# Part 6 – Evaluate Microsoft Foundry agents with real datasets

Monitoring tells you what happened. Evaluation asks whether the answer was useful, grounded, coherent, and safe. A character count or a local dictionary can be a smoke test, but neither is a Foundry evaluation. This article uses the Foundry evaluator and evaluation-run APIs shown in the source article.

## Prerequisites

You need a Foundry project, a model deployment suitable for evaluator judgments, an agent version, and permission to create datasets and evaluations. Evaluator and `azure_ai_agent` target schemas are preview-sensitive; pin the SDK and verify the current reference for your tenant before automation.

```bash
pip install "azure-ai-projects>=2.4.0" azure-identity openai python-dotenv
```

## 1. Make a representative dataset

Store realistic inputs and expected context in JSONL. Include happy paths, ambiguous requests, refusals, tool failures, and regression cases. Do not upload secrets or unnecessary personal data.

```json
{"query":"Summarize the return policy","context":"Returns are accepted within 30 days","expected":"A concise answer mentioning 30 days"}
```

`upload_dataset.py` uploads the file with `project.datasets.upload_file`; it does not manufacture scores locally.

## 2. Choose evaluators

Use built-in evaluators such as coherence or violence where they fit, and a rubric evaluator when your quality definition is domain-specific. A rubric is an evaluator definition judged by a model; it is not a Python `len()` check. `create_evaluation.py` shows the current `TestingCriterionAzureAIEvaluator` and custom data mapping pattern.

Treat evaluator output as evidence, not truth. Review samples, calibrate against human labels, and version the dataset, agent version, evaluator version, and judge deployment together.

## 3. Create and inspect an evaluation run

An evaluation contains criteria and a data source. An evaluation run executes the agent target over the dataset and records per-row results. `run_evaluation.py` creates the eval and run, then polls the run; use the portal or API result endpoint to inspect failures and distributions.

## 4. Continuous evaluation

Run a small regression set on every prompt/tool change, a broader set before release, and scheduled production samples after release. Gate deployments on agreed thresholds, but keep human review for high-impact decisions. Link runs to the agent version and source commit so a score change is actionable.

## Run the sample

```bash
python code/upload_dataset.py ./test-queries.jsonl
python code/create_evaluation.py
python code/run_evaluation.py
```

The scripts require `AZURE_AI_PROJECT_ENDPOINT`, `MODEL_DEPLOYMENT`, `FOUNDRY_AGENT_NAME`, and `FOUNDRY_DATASET_ID` (the upload script prints the ID). API models may change in preview; failures should be treated as a prerequisite/version mismatch, not silently replaced with local metrics.

Continue with [Part 7 – Guardrails](/blog/microsoft-foundry/part7-guardrails). The series then covers [multi-agent orchestration](/blog/microsoft-foundry/part8-multi-agent-orchestration), [hosted agents](/blog/microsoft-foundry/part9-deploying-hosted-agents), and [production operations](/blog/microsoft-foundry/part10-from-notebook-to-production).

---

## Full sample code

- [upload_dataset.py](code/upload_dataset.py)
- [create_evaluation.py](code/create_evaluation.py)
- [run_evaluation.py](code/run_evaluation.py)
