---
title: "How Agents Communicate"
excerpt: "Use the Part 9 retail example to understand direct calls, shared application state, MCP tools, and Agent2Agent communication across deployment boundaries."
slug: microsoft-foundry/part10-agent-to-agent-communication
artifactPath: "Microsoft Foundry/part10-agent-to-agent-communication"
tags: ["azure", "ai-foundry", "sdk", "python", "agents", "a2a", "mcp"]
series: {"slug":"microsoft-foundry","title":"Microsoft Foundry","part":10}
publishAt: "2026-08-09T16:54:00.000Z"
---
---
title: "Microsoft Foundry SDK: Part 10 - How Agents Communicate"
excerpt: "Use the Part 9 retail example to understand direct calls, shared application state, MCP tools, and Agent2Agent communication across deployment boundaries."
slug: microsoft-foundry/part10-agent-to-agent-communication
artifactPath: "microsoft-foundry/part10-agent-to-agent-communication"
tags: ["azure", "ai-foundry", "sdk", "python", "agents", "a2a", "mcp"]
series: {"slug":"microsoft-foundry","title":"Microsoft Foundry","part":10}
publishAt: "2026-09-23T18:00:00.000Z"
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

## First, the Part 9 approach

In the Part 9 handoff example, the application owns the conversation:

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

The agents do not directly call one another. The application is the coordinator.

## Option 1: Pass work directly inside the application

The simplest form of agent communication is ordinary Python code:

```python
draft = run_agent(project_client, shopper_agent, customer_request)
review_prompt = f"Review this draft:\n\n{response_text(draft)}"
review = run_agent(project_client, reviewer_agent, review_prompt)
```

There is no special agent-to-agent protocol here. The application receives text from the first call and includes it in the second call. This is easy to debug because the application can log every request and response.

Use this approach when:

- the agents are deployed in the same Foundry project;
- one application controls the whole workflow; and
- passing text between calls is enough.

## Option 2: Use an application workflow

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

This is still application-owned communication. A workflow makes the order and error handling easier to see, but it does not turn the agents into independent network services.

This is the right mental model for the sequential and concurrent examples in Part 9.

## Option 3: MCP connects an agent to a tool

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

## Option 4: A2A connects independently hosted agents

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

The calling agent sends a task to a standard A2A endpoint. The remote agent processes the task and returns a response. The caller can then use that response in the customer conversation.

The boundary is now larger than a Python function call. It includes:

- an endpoint and agent card;
- authentication and authorization;
- a connection configured in Foundry;
- timeouts and retries;
- a clear contract for the request and response; and
- ownership and monitoring for both sides.

Use A2A when the remote agent is independently hosted, independently owned, or intended to serve multiple callers. Do not add it merely because an application has two prompt agents.

## What changes in the retail example?

With local routing, the application calls the loyalty agent by its configured name:

```python
specialist = run_agent(
    project_client,
    AGENT_NAMES["loyalty"],
    customer_request,
)
```

With A2A, the caller sends the same business request to a remote loyalty endpoint. The caller does not invoke the loyalty agent's Python function directly. Foundry manages the configured A2A connection and the remote protocol boundary.

The business meaning is the same:

```text
"Can I use my loyalty points on this order?"
```

The operational responsibilities are different. The local version is easier to start and debug. The A2A version gives the loyalty team independent deployment and ownership, but requires more setup and failure handling.

## Option 5: Use a service or queue for asynchronous work

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

For a Foundry-to-Foundry A2A connection, the target agent must expose an incoming A2A endpoint. The calling project then needs an A2A connection whose target is that endpoint. The calling agent is configured with the A2A tool or toolbox connection.

The setup sequence is:

1. Create or choose the loyalty agent in the target project.
2. Enable incoming A2A on that agent.
3. Grant the calling identity permission to consume the target agent.
4. Create an A2A connection in the calling project.
5. Add the A2A tool or toolbox to the calling agent.
6. Test the request and inspect both caller and target traces.

The exact authentication mode depends on whether the target is another Foundry agent or an external A2A-compatible service. Use the generally available `a2a` tool for new integrations; treat older preview integrations separately.

## Keep the user-facing answer grounded

Delegation does not automatically make every fact available to the final agent. If the inventory specialist checks stock and the loyalty specialist checks redemption rules, the final response must preserve which result came from which source. Pass evidence explicitly or let the final responding agent perform the necessary tool calls itself.

For the retail request, a safe final answer should distinguish:

- what the loyalty rules allow;
- whether the blue jacket in medium is actually available; and
- what the application knows versus what it still needs to verify.

## Key takeaways

- Part 9 showed agents communicating through application code.
- Workflows make fixed sequences visible but remain application-owned.
- MCP connects agents to tools and data.
- A2A connects independently hosted agents through a standard endpoint.
- Queues and services are often better for asynchronous work.
- Use A2A when the deployment or ownership boundary justifies it, not simply because multiple agents exist.

Next up: **Part 11** - From notebook to production with versioning, blue-green rollouts, and environment management.

---

*Sources: [Connect to an A2A agent endpoint from Foundry Agent Service](https://learn.microsoft.com/azure/foundry/agents/how-to/tools-a2a), [Enable incoming A2A on a Foundry agent](https://learn.microsoft.com/azure/foundry/agents/how-to/enable-agent-to-agent-endpoint), [Agent2Agent authentication](https://learn.microsoft.com/azure/foundry/agents/concepts/agent-to-agent-authentication).*
