---
title: "How Agents Communicate"
excerpt: "Use the Part 9 retail example to understand direct calls, shared application state, MCP tools, and Agent2Agent communication across deployment boundaries."
slug: microsoft-foundry/part10-agent-to-agent-communication
artifactPath: "Microsoft Foundry/part10-agent-to-agent-communication"
tags: []
series: {"slug":"microsoft-foundry","title":"Microsoft Foundry","part":10}
publishAt: "2026-08-09T16:54:00.000Z"
---
# Microsoft Foundry SDK: Part 10 - How Agents Communicate

In Part 9, all of the agents lived inside one application. The application called the handoff agent, selected a specialist, and passed text from one specialist to another.

That is a good starting point, but it is not the only way agents can work together. This article uses the same retail example to explain what changes when agents communicate through different boundaries:

1. A normal function or SDK call inside one application.
2. A shared application workflow that passes one agent's output to another.
3. An MCP tool, where an agent calls a tool but not another agent.
4. An Agent2Agent (A2A) endpoint, where one independently hosted agent calls another.
5. An ordinary service or queue, when the interaction should be asynchronous.

## The same example

The customer asks:

> Can I use my loyalty points to buy the blue trail jacket in medium?

Part 9 created three specialists:

- **Shopper specialist**: decides whether the product fits the customer's needs.
- **Inventory specialist**: checks availability and delivery.
- **Loyalty specialist**: explains points and membership rules.

The important question in Part 10 is not which specialist is best. It is **how one component sends work to another component**.

## What does agent-to-agent communication mean?

An agent is a software component that can interpret a request, decide what to do, and use its instructions and tools to produce a response. When two agents communicate, one agent is asking another agent to do a piece of work instead of doing that work itself.

That sounds similar to a normal function call, but the deployment boundary matters:

- A **function call** stays inside your Python process.
- A **local Foundry call** stays inside your application and project.
- An **A2A call** crosses an endpoint between independently hosted agents.

A2A, short for **Agent2Agent**, is an open protocol for that last case. It defines a common way for a caller to discover an agent's capabilities, send it a task, and receive the result. The caller does not need to know the remote agent's prompt, model deployment, or implementation language. It needs a reachable endpoint, permission to call it, and a clear task to send.

An A2A endpoint publishes an **agent card**. Think of the card as a small profile for the remote agent: it describes what the agent does, which protocol version it supports, and how a caller can reach it. The card is not the conversation itself; it is the information a caller needs before starting one.

### What is an agent card?

An agent card is a metadata document that a remote agent exposes at its A2A endpoint. When a caller (another agent or a service) wants to call a remote agent, it first fetches the agent card to learn:

- **Agent name and description**: What the agent does and who should use it.
- **Skills/tools** (optional): A list of actions the agent can take (e.g., "check_points_balance", "apply_points_to_purchase"). These help the caller understand what work the agent can handle.
- **Example prompts** (optional): Sample requests that work well with this agent.
- **Protocol version**: Which A2A protocol version the agent supports.

To enable A2A on an agent, you create the card once and enable the A2A protocol on the agent endpoint. Foundry then serves the card at the agent's A2A endpoint (for example, `https://.../agents/orch-loyalty/endpoint/protocols/a2a/agentCard/v1.0`). Any caller with permission to reach that endpoint can fetch the card and learn how to talk to the agent.

**Current Foundry setup:** the incoming-A2A endpoint is enabled through the REST API or the Azure AI Projects SDK. The portal wording and availability can vary by Foundry experience, so do not assume that an "Create an agent card" button exists. The update must provide both an `agent_card` and an `agent_endpoint.protocol_configuration.a2a` section.

For example, the SDK configuration is conceptually:

```python
from azure.ai.projects.models import (
    A2AProtocolConfiguration,
    AgentCard,
    AgentCardSkill,
    AgentEndpointConfig,
    ProtocolConfiguration,
    ResponsesProtocolConfiguration,
)

project.agents.update_details(
    agent_name="orch-loyalty",
    agent_endpoint=AgentEndpointConfig(
        protocol_configuration=ProtocolConfiguration(
            responses=ResponsesProtocolConfiguration(),
            a2a=A2AProtocolConfiguration(),
        )
    ),
    agent_card=AgentCard(
        version="1.0",
        description="Answers questions about loyalty points and redemption rules.",
        skills=[
            AgentCardSkill(
                id="loyalty-questions",
                name="Loyalty questions",
                description="Explains loyalty points, eligibility, and redemption rules.",
            )
        ],
    ),
)
```

Foundry serves both `agentCard/v1.0` and `agentCard/v0.3`. Version 1.0 is generally available and should be preferred for new integrations; v0.3 remains available for existing preview clients.

Once the card is created, the agent is discoverable and callable from any remote agent or service that has permission to reach its A2A endpoint.

For new Foundry integrations, this article uses the generally available A2A protocol version 1.0 through the `a2a` tool where the Foundry connection manages protocol negotiation. The direct script also shows the v0.3 card path because that is the version used by the captured working run. For a new direct integration, prefer `agentCard/v1.0` and the corresponding v1.0 client request.

## A baseline from Part 9

Part 9 used application-owned orchestration as its example. In that design, the application owns the conversation:

```text
User
  |
  v
Application
  |
  +--> Handoff agent: "Which specialist should answer?"
  |
  +--> Loyalty specialist: "Answer the customer's question"
```

The application knows every agent name, sends the request, validates the result, and decides what happens next. This is the simplest option when all agents belong to the same application and project.

The agents do not directly call one another. The application is the coordinator. This is one valid communication pattern, but it is not a prerequisite for the patterns below.

## Common communication patterns for agent systems

The following patterns are independent choices. You can use one pattern throughout an application, or combine several when different parts of the system have different needs.

### Option 1: Pass work directly inside the application

One pattern is to pass work directly between agent calls using ordinary application code:

```python
draft = run_agent(project_client, shopper_agent, customer_request)
review_prompt = f"Review this draft:\n\n{response_text(draft)}"
review = run_agent(project_client, reviewer_agent, review_prompt)
```

There is no special agent-to-agent protocol here. The application receives text from the first call and includes it in the second call. This is easy to debug because the application can log every request and response.

Use direct calls when:

- the agents are deployed in the same Foundry project;
- one application controls the whole workflow; and
- passing text between calls is enough.

### Option 2: Use an application workflow

For a fixed process, the application can model the steps as a workflow:

```text
Request
  |
  v
Shopper specialist creates a draft
  |
  v
Reviewer specialist checks the draft
  |
  v
Application returns the final answer
```

This is application-owned communication. A workflow makes the order and error handling easier to see, but it does not turn the agents into independent network services.

Part 9's sequential and concurrent examples are both instances of this general pattern.

### Option 3: MCP connects an agent to a tool

An agent may need to look up inventory or retrieve a loyalty balance. That does not necessarily require another agent. It may need a tool:

```text
Loyalty specialist
  |
  +--> MCP tool: get loyalty balance
  |
  +--> MCP tool: check redemption rules
```

MCP is a tool boundary. The agent asks a tool to perform an operation or retrieve data. It is not, by itself, a protocol for asking another agent to reason about a task.

For the retail example, an inventory API, loyalty database, or order system would usually be exposed as tools. The loyalty specialist remains responsible for explaining the result to the customer.

### Option 4: A2A connects independently hosted agents

Now consider a different organization. The loyalty specialist is owned by a separate team, deployed in another Foundry project, and used by several applications. The retail application should not need to know the specialist's internal prompts, model deployment, or Python code.

With A2A, the communication looks like this:

```text
Retail application agent
  |
  | A2A request over a remote agent endpoint
  v
Loyalty agent owned by another team
  |
  v
A2A response
```

The calling agent sends a task to a standard A2A endpoint. The remote agent processes the task and returns a response. The caller can then use that response in the customer conversation. The remote agent may be another Foundry agent, or an A2A-compatible agent hosted elsewhere.

The boundary is now larger than a Python function call. It includes:

- an endpoint and agent card;
- authentication and authorization;
- a connection configured in Foundry;
- timeouts and retries;
- a clear contract for the request and response; and
- ownership and monitoring for both sides.

Use A2A when the remote agent is independently hosted, independently owned, or intended to serve multiple callers. Do not add it merely because an application has two prompt agents.

### A2A in one sentence

In this example, the retail application sends the customer's question to a remote loyalty agent:

```text
Retail application
  |
  | A2A request over HTTPS
  v
Remote loyalty agent
  |
  v
A2A response
```

The caller does not import the loyalty agent's Python code or know its prompt and model deployment. It needs the remote A2A endpoint, an agent card, an Entra token, and a message to send.

Routing and communication are separate decisions:

1. **Routing** answers which specialist should handle the request.
2. **A2A** answers how to send the request when that specialist is hosted behind a remote agent endpoint.

This article keeps the runnable example intentionally simple: the application routes this test request directly to the loyalty endpoint. A production router can select among several A2A endpoints after this basic call is working.

### Option 5: Use a service or queue for asynchronous work

Not every interaction needs an immediate answer. If a request may take minutes or should be processed in the background, an ordinary service or message queue may be a better fit:

```text
Retail application
  |
  +--> Queue: "Check loyalty eligibility for order 123"
              |
              v
        Loyalty worker
              |
              v
        Result store or callback
```

This is useful for batch checks, long-running tasks, and workloads where the customer does not need an answer in the same request. A2A is designed for agent-to-agent interaction; a queue is designed for reliable asynchronous delivery. They solve different problems.

## Choosing between the options

| Situation | Start with |
| --- | --- |
| Two agents in one Python application | Direct SDK calls |
| A fixed draft-then-review process | Application workflow |
| An agent needs inventory or account data | MCP tool |
| Another team owns the loyalty agent | A2A endpoint |
| The work can finish later | Service or queue |

Start with the smallest boundary that solves the problem. A remote protocol adds useful independence, but it also adds authentication, network failures, versioning, and observability work.

## A2A request flow in Foundry

For a Foundry-to-Foundry A2A connection, the target agent must expose an incoming A2A endpoint. The calling project then needs an A2A connection whose target is the target agent's **A2A base path**. Do not configure the connection target as an `agentCard/v0.3` or `agentCard/v1.0` URL; Foundry resolves the card path itself. The calling agent is configured with the A2A tool or toolbox connection.

The setup sequence is:

1. Create or choose the loyalty agent in the target project.
2. Enable incoming A2A on that agent through the REST API or Python SDK.
3. Grant the calling identity the **Foundry Agent Consumer** role, or a higher role, on the target project or agent.
4. Create an A2A connection in the calling project with the target set to the A2A base path and audience `https://ai.azure.com`.
5. Add the A2A tool to the calling agent.
6. Test the request and inspect both caller and target traces.

The exact authentication mode depends on whether the target is another Foundry agent or an external A2A-compatible service. Use the generally available `a2a` tool for new integrations; treat older preview integrations separately.

## Runnable example: call a remote loyalty agent

This section shows two approaches to call a remote A2A agent. The direct approach has been verified end to end; the routed approach is the Foundry-managed pattern and depends on its connection identity and target-project permissions:

1. **Direct A2A Protocol** (recommended for service-to-agent calls) — stateless and explicit
2. **Routed via SDK** (educational, with Foundry connection setup) — requires pre-configured A2A connections in Foundry

### Approach 1: Direct A2A Protocol

The simplest A2A pattern is to call the remote agent's endpoint directly without creating an intermediate caller agent. This works well when a service or script needs to invoke a remote agent without routing logic.

**How it works:**
1. Get an access token.
2. Resolve the remote agent's card at its A2A endpoint.
3. Create an A2A client and send a message.
4. Receive the structured response.

**Why use this:**
- **Stateless**: No agents created, no connections configured.
- **Clear**: The full A2A flow is visible in the code.
- **Testable**: Easy to debug from a local script or service.
- **Service-compatible**: Works equally well from Python, Node.js, Go, etc.

**Example: `01_a2a_call_direct.py`**

```python
import asyncio
import os
import httpx
from azure.identity import DefaultAzureCredential
from a2a.client import A2ACardResolver, ClientConfig, create_client
from a2a.helpers import new_text_message
from a2a.types.a2a_pb2 import Role, SendMessageRequest

endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
agent_name = "orch-loyalty"

# Full A2A base URL for this agent
A2A_BASE_URL = f"{endpoint}/agents/{agent_name}/endpoint/protocols/a2a"
AGENT_CARD_PATH = "agentCard/v0.3"


async def main():
    credential = DefaultAzureCredential()
    token = credential.get_token("https://ai.azure.com/.default").token

    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=httpx.Timeout(120.0),
    ) as httpx_client:
        # Resolve the agent card
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=A2A_BASE_URL,
            agent_card_path=AGENT_CARD_PATH,
        )
        agent_card = await resolver.get_agent_card()

        # Create a non-streaming A2A client
        config = ClientConfig(streaming=False, httpx_client=httpx_client)
        client = await create_client(agent=agent_card, client_config=config)

        # Send a message to the agent
        message = new_text_message("Hello, what can you do?", role=Role.ROLE_USER)
        request = SendMessageRequest(message=message)

        async for response in client.send_message(request):
            print(response)

        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

**To run:**

```bash
python 01_a2a_call_direct.py
```

**Example output:**

When successful, you will see the resolved agent card and the structured response from the remote loyalty agent:

```
Project endpoint: https://blog-wymedia-resource.services.ai.azure.com/api/projects/blog-wymedia-project
Loyalty A2A endpoint: https://blog-wymedia-resource.services.ai.azure.com/api/projects/blog-wymedia-project/agents/orch-loyalty/endpoint/protocols/a2a
User request: Can I use my loyalty points to buy the blue trail jacket in medium?

--- Resolving agent card ---
Agent card resolved: orch-loyalty
--- Sending message to remote agent ---
--- Agent response ---
task {
  id: "resp_07e21cf02ca041a6006ab41620ab448190a1a24889f61249ee"
  context_id: "ctxt_0b5776197a1448cdb380424cb6475ff1"
  status {
    state: TASK_STATE_COMPLETED
    timestamp {
      seconds: 1790187042
    }
  }
  artifacts {
    artifact_id: "msg_07e21cf02ca041a6006ab4162167c88190847fecc7cbe94313"
    parts {
      text: "I can help with that, but I can't see your account balance or whether the jacket is eligible for points payment.

In general, loyalty points can sometimes be used:
- at checkout as a discount
- toward part or all of a purchase
- only on eligible items or minimum order values

To check for the blue trail jacket in medium, you'll want to verify:
1. That the item is in stock in your size
2. Whether it's eligible for points redemption
3. Your available points balance in your account
4. Any redemption rules, like minimum spend or exclusions

If you want, I can help you figure out:
- how to check eligibility on the product page
- how loyalty points usually work at checkout
- what to look for in the terms and conditions"
    }
  }
}

--- A2A call completed ---
```

This output shows:
- The A2A endpoint was resolved successfully
- The agent card for `orch-loyalty` was fetched
- The message was delivered to the remote agent
- The remote agent processed the request and returned a complete, business-relevant response

This approach is the recommended starting point for most use cases. It still requires incoming A2A to be enabled on the target agent and the caller identity to have permission to read and invoke that endpoint, but it does not require a project-level `RemoteA2A` connection or an intermediate caller agent.

---

### Approach 2: Routed A2A Call via SDK (Agent with A2ATool)

For more complex workflows, you may want to use Foundry's Agent SDK to create a temporary caller agent that invokes the remote agent as a tool. This is useful when:

- The caller is itself an agent that needs routing logic.
- The caller wants to combine A2A with other tools or agents.
- You want the caller's reasoning and traces to be visible in Foundry.

**How it works:**
1. Route the request to the appropriate specialist (shopper, inventory, or loyalty).
2. Create a temporary caller agent with an A2ATool connected to a pre-configured A2A connection.
3. Use the Responses API to invoke the caller agent.
4. The A2ATool automatically handles the connection to the remote agent.

**Why use this:**
- **Flexible**: A2A tools can be combined with other tools and agents.
- **Traced**: The entire interaction is visible in Foundry's agent traces.
- **Routing-aware**: Integrates naturally with agent routing logic.

**Setup: Pre-configured A2A Connections**

Before running the script, you must create an A2A connection in the calling Foundry project. The current Foundry documentation exposes this under **Tools > Connect tool > Custom > Agent2Agent (A2A)**; portal labels may differ by experience.

1. Create a new `RemoteA2A` connection:
   - **Name**: `loyalty-agent-connection` (or your chosen name)
   - **Type**: `RemoteA2A`
   - **Target**: The remote agent's A2A base path, e.g., `https://<endpoint>/api/projects/<project>/agents/orch-loyalty/endpoint/protocols/a2a`
   - **Audience**: `https://ai.azure.com`
   - **Auth**: `Entra Agent Identity` or project managed identity
2. Test the connection in the portal to verify connectivity.
3. Repeat for other specialists (inventory, shopper) if needed.

**Example: `02_a2a_call_routed.py`**

This script creates a temporary calling agent and invokes a remote A2A agent through a pre-configured connection. The setup requires creating the A2A connection in Foundry before running the script.

**Prerequisites:**

1. **Create the A2A connection in Foundry:**
   - Go to [Microsoft Foundry](https://ai.azure.com/) → **Tools** → **Connect tool** → **Custom** → **Agent2Agent (A2A)**.
   - Set:
     - **Name**: loyalty-agent-connection
     - **Target endpoint**: https://blog-wymedia-resource.services.ai.azure.com/api/projects/blog-wymedia-project/agents/orch-loyalty/endpoint/protocols/a2a
     - **Audience**: https://ai.azure.com
     - **Authentication**: Entra Agent Identity or project managed identity
   - Do not append `/agentCard/v0.3` or `/agentCard/v1.0` to the target.
   - Test and save.

2. **Grant permissions:**
   - The identity selected by the connection must have the **Foundry Agent Consumer** role on the target project or target agent.

3. **Update .env:**
   ```
   FOUNDRY_PROJECT_ENDPOINT=https://blog-wymedia-resource.services.ai.azure.com/api/projects/blog-wymedia-project
   MODEL_DEPLOYMENT=gpt-4o
   A2A_LOYALTY_CONNECTION_NAME=loyalty-agent-connection
   A2A_CALLER_AGENT_NAME=orcha2a-caller
   TEST_PROMPT=Can I use my loyalty points to buy the blue trail jacket in medium?
   ```

### Why the direct script can work while the routed script returns 404

The two scripts use different caller identities. The direct script obtains a Microsoft Entra token locally through `DefaultAzureCredential` and calls the agent-card endpoint itself. The routed script invokes `A2ATool` inside Foundry, so Foundry fetches the card using the identity configured on the A2A connection.

Consequently, a successful direct call does not prove that the routed connection is authorized. If the routed call reports `Failed to fetch agent card ... 404`, check:

1. Incoming A2A is enabled on the target agent, with both the responses and A2A protocols configured.
2. The connection target is the A2A base path, not an `agentCard` URL.
3. The connection audience is `https://ai.azure.com`.
4. The connection's agent or project identity has **Foundry Agent Consumer** or higher on the target project or agent.
5. The endpoint account, project name, and agent name are exact.

You can independently verify the target card with a local Entra token:

```powershell
$token = az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv
Invoke-RestMethod `
  -Uri "https://<account>.services.ai.azure.com/api/projects/<project>/agents/<agent>/endpoint/protocols/a2a/agentCard/v1.0" `
  -Headers @{ Authorization = "Bearer $token" }
```

If this succeeds locally but the routed script still returns 404, the remaining problem is the Foundry connection identity or its role assignment, not the Python routing logic.

**Script:**

```python
import os
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    A2AProtocolVersion,
    A2ATool,
    PromptAgentDefinition,
)
from azure.identity import DefaultAzureCredential

project_endpoint = os.environ.get('FOUNDRY_PROJECT_ENDPOINT')
model_deployment = os.environ.get('MODEL_DEPLOYMENT')
connection_name = os.environ.get('A2A_LOYALTY_CONNECTION_NAME')
caller_agent_name = os.environ.get('A2A_CALLER_AGENT_NAME')
test_prompt = os.environ.get('TEST_PROMPT')

# Authenticate and get the project client
project = AIProjectClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential(),
)

# Retrieve the pre-configured A2A connection
connection = project.connections.get(connection_name)

# Create an A2A tool that uses the connection
loyalty_tool = A2ATool(
    a2a_version=A2AProtocolVersion.V1_0,
    project_connection_id=connection.id,
)

# Create a temporary calling agent with the tool
caller = project.agents.create_version(
    agent_name=caller_agent_name,
    definition=PromptAgentDefinition(
        model=model_deployment,
        instructions='Use the loyalty specialist tool to answer customer questions about points and purchases.',
        tools=[loyalty_tool],
    ),
)

# Invoke the agent through the Responses API
openai = project.get_openai_client()
response = openai.responses.create(
    tool_choice='required',
    input=test_prompt,
    extra_body={
        'agent_reference': {
            'name': caller.name,
            'type': 'agent_reference',
        }
    },
)

print(f'Response: {response.output_text}')
```

**To run:**

```bash
python 02_a2a_call_routed.py
```

**Troubleshooting:** If the script fails with a 404 error:
- Verify the A2A connection exists and passes its test in the Foundry portal.
- Check that the target agent's A2A endpoint is correct and accessible.
- Ensure the calling identity has **Foundry Agent Consumer** permission on the target project.
- Verify the target agent has incoming A2A enabled.

---

## Summary

Both approaches deliver A2A communication; choose based on your use case:

| Aspect | Direct A2A Protocol | Routed via SDK |
|--------|-------------------|-----------------|
| **Setup** | No portal config needed | Requires A2A connection in portal |
| **Complexity** | Simpler (explicit token, fetch card, send message) | More involved (agent creation, tool attachment) |
| **Best for** | Scripts, services, first integration | Agent workflows, routing logic, combined tools |
| **Observability** | Application-level logs | Visible in Foundry traces and UI |
| **Error handling** | Explicit in code | Foundry-managed |

**Direct A2A Protocol** is the recommended starting point for most applications. It requires minimal setup and works from any language or platform.

**Routed via SDK** is valuable when your caller is itself an agent that needs to combine A2A calls with other tools or apply complex routing logic.

For production use, both patterns should include:
- Timeout and retry logic.
- Structured logging with correlation IDs.
- Health checks on the remote agent's endpoint.
- Permission audits (ensure callers have Foundry Agent Consumer role).
