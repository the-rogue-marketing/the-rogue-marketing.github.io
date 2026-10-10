---
layout: post
title: "Orchestrating Hierarchical Multi-Agent Teams: The Supervisor Pattern in PydanticAI and LangGraph"
description: "Architect complex multi-agent teams using the Supervisor pattern. Combine LangGraph state machines with type-safe PydanticAI worker agents for enterprise pipelines."
author: professor-xai
categories: [ai-agents, pydantic-ai, python]
image: assets/images/cheap-ai-agent-tutorial.webp
featured: true
last_modified_at: 2026-10-05
keywords: "supervisor pattern pydanticai, langgraph multi agent hierarchy, autonomous agent orchestration python, type safe multi agent systems"
faq:
  - question: "What is the Supervisor multi-agent pattern?"
    answer: "A hierarchical design where a central Supervisor agent evaluates goals, creates sub-tasks, delegates work to specialized worker agents, reviews outputs, and synthesizes the final response."
  - question: "Why combine LangGraph with PydanticAI?"
    answer: "LangGraph provides cyclic state graph orchestration, checkpointing, and human-in-the-loop approval, while PydanticAI guarantees that data passed between nodes is type-safe and validated."
  - question: "How do you prevent infinite delegation loops in supervisor agents?"
    answer: "Set an explicit `max_iterations` counter in your state graph. If the loop counter exceeds the limit, force the graph to route to a terminal summarizer node."
---

Single-agent prototypes fail when tasked with multi-domain enterprise workflows. An agent asked to simultaneously browse the web, write SQL queries, verify mathematical models, and write marketing copy eventually hallucinates or loses track of its primary objective.

The solution is the **Supervisor Pattern**: a central orchestrator that breaks problems down and delegates to specialized worker agents with dedicated toolsets.

---

## 1. Architecture: The Hierarchical Command Structure

```
                          ┌───────────────────────┐
                          │   Supervisor Agent    │
                          │   (State Orchestrator)│
                          └───────────┬───────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         ▼                            ▼                            ▼
┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
│  Search Worker  │          │  SQL Analyst    │          │  Copywriter     │
│  (Tavily Tools) │          │  (Postgres Tool)│          │  (Brand Guide)  │
└─────────────────┘          └─────────────────┘          └─────────────────┘
```

---

## 2. Implementation with PydanticAI & LangGraph

```python
from typing import Literal
from pydantic import BaseModel, Field
from pydantic_ai import Agent

class RoutingDecision(BaseModel):
    next_worker: Literal["sql_analyst", "web_researcher", "FINISH"]
    instructions_for_worker: str

supervisor = Agent(
    "google-gla:gemini-2.5-flash",
    result_type=RoutingDecision,
    system_prompt="You are an enterprise research supervisor. Route user requests to specialists or declare FINISH."
)

sql_worker = Agent("google-gla:gemini-2.5-flash", system_prompt="Execute SQL queries against enterprise warehouses.")
web_worker = Agent("google-gla:gemini-2.5-flash", system_prompt="Search live documentation and technical feeds.")

async def execute_task(user_query: str):
    context = user_query
    for iteration in range(5):
        decision = await supervisor.run(f"Current state:
{context}
Decide next step.")
        route = decision.data

        if route.next_worker == "FINISH":
            print("🏁 Workflow completed successfully!")
            break

        if route.next_worker == "sql_analyst":
            worker_result = await sql_worker.run(route.instructions_for_worker)
            context += f"
[SQL Worker Output]: {worker_result.data}"
        elif route.next_worker == "web_researcher":
            worker_result = await web_worker.run(route.instructions_for_worker)
            context += f"
[Web Worker Output]: {worker_result.data}"

    return context
```

---

## 3. Enterprise Benefits

1. **Isolated Prompts**: Workers only carry specialized instructions, avoiding prompt pollution and token bloat.
2. **Modular Toolsets**: Security credentials (e.g. database write access) remain isolated exclusively to the SQL worker.
3. **Resilient Error Recovery**: If a worker fails, the supervisor observes the error and re-prompts or routes to a fallback agent.
