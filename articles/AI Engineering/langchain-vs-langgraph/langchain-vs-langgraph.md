---
title: "LangChain vs LangGraph: What's the Difference (with Python Examples)"
excerpt: "A practical comparison of LangChain and LangGraph with Python examples for chains, tool use, state, branching, and retries."
slug: ai-engineering/langchain-vs-langgraph
artifactPath: "AI Engineering/langchain-vs-langgraph"
tags: ["Python", "LangChain", "LangGraph", "LLM Engineering"]
series: null
publishAt: "2026-09-01T19:27:00.000Z"
---
# LangChain vs LangGraph: What’s the Difference (with Python Examples)

If you're building LLM apps in Python, **LangChain** and **LangGraph** solve related but different problems:

- **LangChain** is a framework for building LLM-powered chains, tools, retrieval pipelines, and agents quickly.
- **LangGraph** is an orchestration layer for **stateful, multi-step, and loop-heavy workflows**, especially when you need deterministic control and resumability.

Think of it like this: use **LangChain** for *capabilities* (prompting, tools, RAG, model wrappers), and **LangGraph** for *workflow control* (state machine style execution across steps).

---

## Mental model

### LangChain is best when:

- You want to prototype fast.
- A linear chain or standard agent loop is enough.
- You care more about developer speed than strict flow control.

### LangGraph is best when:

- You need explicit states, branching, retries, and loops.
- You need durable execution/checkpointing.
- You’re building production-grade multi-agent or human-in-the-loop flows.

---

## 1) Simple Q&A flow in LangChain

This is the classic "one request in, one answer out" style.

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

prompt = ChatPromptTemplate.from_template(
    "Explain {topic} to a software engineer in 5 bullet points."
)

chain = prompt | llm | StrOutputParser()

result = chain.invoke({"topic": "vector databases"})
print(result)
```

**Why this is LangChain territory:** it is linear, concise, and doesn't require explicit state transitions.

---

## 2) Tool-calling agent in LangChain

LangChain also makes it easy to expose tools to an LLM.

```python
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

@tool
def usd_to_eur(amount: float) -> float:
    """Convert USD to EUR with a fake fixed rate for demo purposes."""
    return round(amount * 0.92, 2)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
tools = [usd_to_eur]

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful finance assistant."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

response = executor.invoke({"input": "Convert 120 USD to EUR"})
print(response["output"])
```

Great for many use cases, but complex control-flow logic can become harder to reason about as the app grows.

---

## 3) Stateful workflow with branching in LangGraph

Now let's model a workflow where we:
1. classify a user request,
2. branch to either "billing" or "technical" handling,
3. return a final response.

```python
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END

class TicketState(TypedDict):
    user_text: str
    category: str
    response: str

def classify(state: TicketState) -> TicketState:
    text = state["user_text"].lower()
    category = "billing" if "invoice" in text or "refund" in text else "technical"
    return {**state, "category": category}

def handle_billing(state: TicketState) -> TicketState:
    return {**state, "response": "Routing to billing workflow and refund policy checks."}

def handle_technical(state: TicketState) -> TicketState:
    return {**state, "response": "Routing to technical troubleshooting workflow."}

def route_by_category(state: TicketState) -> Literal["billing_node", "technical_node"]:
    return "billing_node" if state["category"] == "billing" else "technical_node"

graph = StateGraph(TicketState)
graph.add_node("classify", classify)
graph.add_node("billing_node", handle_billing)
graph.add_node("technical_node", handle_technical)

graph.add_edge(START, "classify")
graph.add_conditional_edges("classify", route_by_category)
graph.add_edge("billing_node", END)
graph.add_edge("technical_node", END)

app = graph.compile()

output = app.invoke({"user_text": "I need a refund for this invoice", "category": "", "response": ""})
print(output["response"])
```

**Why this is LangGraph territory:** explicit state + explicit transitions + branch control.

---

## 4) Retry loop pattern (easy in LangGraph)

Another common production need is iterative refinement with a stop condition.

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class DraftState(TypedDict):
    draft: str
    score: int
    attempts: int

def write_draft(state: DraftState) -> DraftState:
    # Pretend we generated/updated text with an LLM
    new_draft = state["draft"] + " Improved."
    return {**state, "draft": new_draft, "attempts": state["attempts"] + 1}

def score_draft(state: DraftState) -> DraftState:
    # Dummy scoring logic for demo
    score = min(10, len(state["draft"]) // 15)
    return {**state, "score": score}

def should_continue(state: DraftState) -> str:
    if state["score"] >= 8:
        return END
    if state["attempts"] >= 5:
        return END
    return "write"

graph = StateGraph(DraftState)
graph.add_node("write", write_draft)
graph.add_node("score", score_draft)

graph.add_edge(START, "write")
graph.add_edge("write", "score")
graph.add_conditional_edges("score", should_continue)

app = graph.compile()
result = app.invoke({"draft": "Initial version.", "score": 0, "attempts": 0})
print(result)
```

This loop is possible in raw LangChain too, but in LangGraph it is represented as a first-class execution graph, which is easier to inspect and maintain.

---

## Practical decision guide

Use **LangChain first** when:

- your flow is straightforward,
- you mainly need prompts, models, tools, and retrieval,
- and time-to-first-working-version matters most.

Use **LangGraph** when:

- your app has branching/loops/human approvals,
- you need recoverability and durable state,
- and you want execution behavior to be explicit and testable.

In real projects, many teams use both:

- **LangChain** for model/tool abstractions and reusable components,
- **LangGraph** to orchestrate those components in reliable workflows.

---

## Final takeaway

**LangChain helps you build LLM capabilities quickly. LangGraph helps you run those capabilities reliably at production workflow scale.**

Start simple with LangChain, then introduce LangGraph where control-flow and durability become the bottleneck.
