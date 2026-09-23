---
title: "How Agents Communicate"
excerpt: "Build up from a direct A2A call to a Foundry agent with the A2A tool and a RemoteA2A connection."
slug: microsoft-foundry/part10-agent-to-agent-communication
artifactPath: "Microsoft Foundry/part10-agent-to-agent-communication"
tags: ["azure", "ai-foundry", "sdk", "python", "agents", "a2a", "mcp"]
series: {"slug":"microsoft-foundry","title":"Microsoft Foundry","part":10}
publishAt: "2026-08-09T16:54:00.000Z"
---
# Microsoft Foundry SDK: Part 10 - How Agents Communicate

In Part 9, the retail agents lived inside one application. The application selected a specialist and passed text between agent calls. That is the right place to start because it keeps the control flow visible.

This part adds a larger boundary in two steps:

1. Call a remote Foundry agent directly through the A2A protocol.
2. Let a Foundry caller agent use that remote agent through the `A2ATool` and a `RemoteA2A` project connection.

The second example is deliberately optional. First make the direct call work. Then add Foundry-managed routing, identity, and tracing.

## The example

The customer asks:

> Can I use my loyalty points to buy the blue trail jacket in medium?

The loyalty specialist is independently hosted behind an A2A endpoint. The caller does not import its Python code or know its prompt or model deployment.

An A2A endpoint publishes an **agent card**. The card describes the agent, its skills, and the protocol version. A caller resolves the card before sending a task.

The communication boundary is different from MCP:

```text
MCP:  agent -> tool or data service
A2A:  agent or application -> independently hosted agent
```

Use an MCP tool for inventory, account data, or another deterministic operation. Use A2A when another team owns the reasoning agent, the agent is independently deployed, or several applications need the same agent.

## Prerequisites

- An Azure subscription and a Microsoft Foundry project.
- A deployed model and a loyalty agent named `orch-loyalty`.
- Incoming A2A enabled on the loyalty agent.
- An identity with permission to read and invoke the target agent.
- Azure CLI authentication (`az login`) or another `DefaultAzureCredential` source.

Incoming A2A is enabled through the REST API or the Azure AI Projects SDK. The current Foundry portal does not provide this configuration in every experience. The update must provide both an agent card and A2A protocol configuration.

For a new integration, prefer A2A v1.0. The first script uses the v0.3 card path because that is the compatibility path used by the verified run in this article. Set `A2A_AGENT_CARD_PATH=agentCard/v1.0` when the target card and installed SDK are configured for v1.0.

## Level 1: direct A2A protocol

Start with the smallest useful boundary: a local Python process calls the remote agent endpoint directly.

The flow is:

1. Load the project and A2A endpoint from `.env`.
2. Obtain an Entra token for `https://ai.azure.com/.default`.
3. Resolve the target agent card.
4. Create an A2A client.
5. Send a text message and print the structured task response.

The complete runnable example is [`code/01_a2a_call_direct.py`](code/01_a2a_call_direct.py).

Install the dependencies and create the configuration:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

For this first level, fill in:

```text
FOUNDRY_PROJECT_ENDPOINT=https://<account>.services.ai.azure.com/api/projects/<project>
A2A_LOYALTY_ENDPOINT=https://<account>.services.ai.azure.com/api/projects/<project>/agents/<agent>/endpoint/protocols/a2a
A2A_AGENT_CARD_PATH=agentCard/v0.3
LOYALTY_TEST_PROMPT=Can I use my loyalty points to buy the blue trail jacket in medium?
```

Run it from the `code` folder:

```powershell
python .\01_a2a_call_direct.py
```

A successful call resolves the card, sends the request, and returns a completed task:

```text
Project endpoint: https://blog-wymedia-resource.services.ai.azure.com/api/projects/blog-wymedia-project
Loyalty A2A endpoint: https://blog-wymedia-resource.services.ai.azure.com/api/projects/blog-wymedia-project/agents/orch-loyalty/endpoint/protocols/a2a
User request: Can I use my loyalty points to buy the blue trail jacket in medium?

--- Resolving agent card ---
Agent card resolved: orch-loyalty
--- Sending message to remote agent ---
--- Agent response ---
task {
  id: "resp_0ff80d2ba49a21d6006ab41aebf0508190ae524e5d10934625"
  context_id: "ctxt_a9fa28f505814372b1c7648295ec74b7"
  status {
    state: TASK_STATE_COMPLETED
    timestamp {
      seconds: 1790188269
    }
  }
  artifacts {
    artifact_id: "msg_0ff80d2ba49a21d6006ab41aec85708190a88996d7c844cef7"
    parts {
      text: "You may be able to use loyalty points toward that purchase, but I can’t see your account balance or confirm item eligibility from here.

In general, whether you can use points depends on:
- your available points balance
- whether the blue trail jacket in medium is eligible for points redemption
- any restrictions on combining points with other discounts or promotions

If you want, I can help you figure out:
- how loyalty points usually apply at checkout
- whether points can be used on sale items
- how to check the jacket’s eligibility in your account or cart

If you share the store or loyalty program name, I can give more specific guidance."
    }
  }
}
--- A2A call completed ---
```

This is the best diagnostic baseline. If this fails, do not add an A2A tool yet. Check the endpoint, agent card path, incoming-A2A configuration, RBAC, and the token first.

## Level 2: Foundry A2ATool and RemoteA2A

Once the direct call works, move the same request into a Foundry prompt agent. The caller agent can then combine A2A with its own instructions, routing logic, traces, and other tools.

The official Foundry pattern is:

1. Create a project connection of type `RemoteA2A`.
2. Point it at the target agent's **A2A base path**, not its agent-card URL.
3. Use the audience `https://ai.azure.com`.
4. Grant the connection identity **Foundry Agent Consumer** or a higher role on the target project or agent.
5. Attach an `A2ATool` to a prompt agent.
6. Invoke that caller through the Responses API.

The connection target should look like this:

```text
https://<account>.services.ai.azure.com/api/projects/<project>/agents/<agent>/endpoint/protocols/a2a
```

Do not append `/agentCard/v0.3` or `/agentCard/v1.0` to the connection target. Foundry resolves the card and negotiates the protocol for the A2A tool.

Create the connection in Microsoft Foundry under **Tools > Connect tool > Custom > Agent2Agent (A2A)**. Use the connection name in `.env`:

```text
MODEL_DEPLOYMENT=<model-deployment>
A2A_LOYALTY_CONNECTION_NAME=loyalty-agent-connection
A2A_CALLER_AGENT_NAME=orcha2a-caller
```

The complete second example is [`code/02_a2a_call_with_tool.py`](code/02_a2a_call_with_tool.py). Its essential tool definition follows the Azure sample:

```python
connection = project.connections.get(connection_name)

loyalty_tool = A2ATool(
    a2a_version=A2AProtocolVersion.V1_0,
    project_connection_id=connection.id,
)

caller = project.agents.create_version(
    agent_name=caller_agent_name,
    definition=PromptAgentDefinition(
        model=model_deployment,
        instructions="Use the loyalty specialist to answer customer questions.",
        tools=[loyalty_tool],
    ),
)
```

The script creates a temporary caller agent, invokes it through `openai.responses.create`, prints the answer, and deletes the temporary version in `finally`. This is useful when the caller itself needs to reason about which remote specialist to use or combine the A2A tool with other tools.

Run it only after the connection and permissions are ready:

```powershell
python .\02_a2a_call_with_tool.py
```

A successful run creates the caller version, routes the request to the loyalty specialist, and returns the remote agent's answer:

```text
Looking up A2A connection: loyalty-agent-connection
  Connection ID: /subscriptions/c396918f-565f-458c-87b5-4dfe9b6959a8/resourceGroups/RG-BLOG-WYMEDIA/providers/Microsoft.CognitiveServices/accounts/blog-wymedia-resource/projects/blog-wymedia-project/connections/loyalty-agent-connection
  Connection type: RemoteA2A

Caller agent: orcha2a-caller (version 9)
User request: Can I use my loyalty points to buy the blue trail jacket in medium?
Routed to specialist: loyalty
Using A2A connection: loyalty-agent-connection
--- Agent response ---

Yes—if the blue trail jacket in medium is eligible for loyalty redemption, you can
usually apply points toward the purchase.

I can’t confirm your exact redemption amount or remaining balance without your account
details, but in general:
- If your points cover the full price, you can pay entirely with points.
- If not, you’d use points for part of it and pay the rest another way.

If you want, I can also help you check:
1. whether that jacket is eligible, and
2. how many points you’d need.

Deleted temporary caller version 9.
```

The version number is assigned by Foundry and can differ between runs. The script deletes the temporary version after the response.

## Why the two levels can behave differently

The direct script authenticates as the local user through `DefaultAzureCredential`. The `A2ATool` call runs inside Foundry and uses the identity configured on the `RemoteA2A` connection. Therefore, a successful direct call does not prove that the routed call is authorized.

For `Failed to fetch agent card ... 404`, check these in order:

1. Incoming A2A is enabled on the target agent.
2. The connection target is the A2A base path, not an `agentCard` URL.
3. The audience is `https://ai.azure.com`.
4. The connection identity has **Foundry Agent Consumer** or higher on the target.
5. The account, project, and agent names are exact.
6. The connection uses the GA `a2a` tool and A2A v1.0 rather than an old preview configuration.

Verify the target independently before debugging the caller agent:

```powershell
$token = az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv
Invoke-RestMethod `
  -Uri "https://<account>.services.ai.azure.com/api/projects/<project>/agents/<agent>/endpoint/protocols/a2a/agentCard/v1.0" `
  -Headers @{ Authorization = "******" }
```

If this succeeds but the A2A tool returns 404 or 403, the remaining issue is in the Foundry connection identity, target, or role assignment—not in the basic A2A message flow. In this example, assigning **Foundry Agent Consumer** to the caller agent identity on the target project allowed the managed call to complete.

## Summary

Build the integration in this order:

| Level | Boundary | Best for |
| --- | --- | --- |
| 1 | Direct A2A client | First integration, diagnostics, services, explicit control |
| 2 | Foundry `A2ATool` + `RemoteA2A` | Agent routing, Foundry traces, reusable managed connections |

The direct example proves that the remote endpoint and protocol work. The A2A tool adds a Foundry-managed caller on top of that known-good foundation. Keeping those steps separate makes failures easier to diagnose and gives the reader a useful result at every stage.

For production, add timeouts, retries with backoff, structured correlation IDs, health checks, permission reviews, and monitoring on both caller and target.

## Microsoft Learn resources

- [Connect to an A2A agent endpoint from Foundry Agent Service](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/agent-to-agent) — configure a `RemoteA2A` connection and use the `A2ATool`.
- [Enable an A2A endpoint on a Foundry agent](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/enable-agent-to-agent-endpoint) — expose the loyalty agent and verify its agent card.
- [Agent2Agent (A2A) authentication](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/agent-to-agent-authentication) — understand agent identities, audiences, authentication modes, and RBAC troubleshooting.
