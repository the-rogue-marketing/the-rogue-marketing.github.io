---
layout: post
title: "Orchestrating Multi-Step AI Agents: Integrating Pydantic AI and LangGraph with Gemini 3.1 Pro"
description: "A production-grade developer's guide to building stateful, cyclical, and multi-step AI agents by combining LangGraph's stateflows with Pydantic AI's type-safe task execution."
author: professor-xai
categories: [ai-api, langgraph, pydantic-ai, engineering]
image: assets/images/llm-api-providers.jpg
featured: true
last_modified_at: 2026-05-21
keywords: "langgraph pydantic ai tutorial, multi step ai agents, gemini api agent orchestration, stateful ai workflows python, pydantic ai langgraph integration"
---

When building simple autonomous systems, single-agent loops are highly effective. A single agent (such as a Pydantic AI agent) is wrapped with tools, passed a prompt, and left to execute in a self-correcting loop until it achieves its objective.

However, as business logic grows in complexity, single-agent systems inevitably break down. When an application requires a highly structured, multi-step workflow—such as researching a topic, compiling a technical draft, auditing it against rigorous editorial guidelines, and conditionally looping back to the research phase if it fails review—a single agent is prone to "context drift," tool confusion, and loop traps.

In **May 2026**, the industry standard for building these advanced systems is a **Hybrid Agent Architecture**: using **LangGraph** to manage the global state, multi-step transitions, and conditional routing loops, while utilizing **Pydantic AI** inside individual graph nodes to handle type-safe reasoning, structured parsing, and tools.

In this guide, we will design and build an enterprise-grade **Technical Content Compilation System**. We will walk through setting up our environment with **uv**, architecting our hybrid graph state, and writing complete, non-stubbed Python code powered by `Gemini 3.1 Pro`.

---

## 🏗️ The Hybrid Architecture: Stateflow vs. Cognitive Execution

To build complex systems, we must separate the **global state machine** from individual **cognitive execution tasks**:

```
                       ┌──────────────────────────────┐
                       │      Global State (Dict)     │
                       └──────────────┬───────────────┘
                                      │
                                      ▼
                      ┌────────────────────────────────┐
                      │    LangGraph State Machine     │
                      └───────┬────────────────┬───────┘
                              │                │
                              ▼                ▼
                     ┌────────────────┐   ┌────────────────┐
                     │ Research Node  │   │  Drafting Node │
                     │  (Pydantic AI) │   │  (Pydantic AI) │
                     └────────────────┘   └────────────────┘
```

1.  **LangGraph (The Stateful Orchestrator):** Manages the global state of the application. It defines the "nodes" (individual processing steps), the "edges" (the transitions between steps), and "conditional edges" (routing decisions based on agent output). It guarantees complete execution control and easy "human-in-the-loop" validation hooks.
2.  **Pydantic AI (The Task Executor):** Runs the specific reasoning work inside each LangGraph node. It provides strict Pydantic model validation and type-safe tool calling, ensuring that the data passed back to the global LangGraph state is always formatted correctly.

---

## 🛠️ Setting up the Hybrid Workspace with `uv`

First, let's bootstrap our virtual python workspace and install our production dependencies using Astrid's ultra-fast manager, `uv`.

Open your terminal and run:

```bash
# 1. Initialize our workspace
uv init multi-agent-graph
cd multi-agent-graph

# 2. Add modern Pydantic AI, LangGraph, and Uvicorn
uv add langgraph pydantic-ai google-genai pydantic

# 3. Establish our development directory
mkdir -p app/services
touch app/main.py app/services/graph_service.py
```

This guarantees an isolated virtual environment resolved in milliseconds.

---

## 📐 Defining our Global State and Structured Schemas

Our multi-step assistant will coordinate three nodes:
1.  **Research Agent:** Ingests a topic, queries simulated web databases, and outputs a list of structured technical facts.
2.  **Drafting Agent:** Ingests the technical facts and compiles a long-form Markdown technical blog post.
3.  **Editor Agent:** Ingests the compiled draft, audits it against style guidelines, and determines if it is approved or requires revision (triggering a loop back).

Let's write our strict schemas and the global LangGraph state in `app/services/graph_service.py`:

```python
import os
import sys
from typing import TypedDict, list, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from langgraph.graph import StateGraph, START, END

# --- 1. Define Structured Schemas for Agent Tasks ---

class ResearchNodeOutput(BaseModel):
    source_facts: list[str] = Field(description="Exhaustive list of verified technical facts extracted from research.")
    relevant_apis: list[str] = Field(default_factory=list, description="APIs or libraries mentioned in research.")

class EditorialAudit(BaseModel):
    approved: bool = Field(description="True if the draft complies with all editorial guidelines, False otherwise.")
    redline_issues: list[str] = Field(default_factory=list, description="Specific formatting or factual issues that must be corrected.")
    revision_instructions: Optional[str] = Field(None, description="Detailed instructions for the research or drafting agents to resolve issues.")

# --- 2. Define the Global LangGraph State Dictionary ---

class ContentWorkflowState(TypedDict):
    topic: str                             # The input target topic
    research_data: Optional[ResearchNodeOutput] # Compiled technical research
    current_draft: Optional[str]           # The current compiled Markdown text
    audit_report: Optional[EditorialAudit] # The compiled editor review
    iteration_count: int                   # Prevent infinite looping
```

---

## 🤖 Building the Specialized Pydantic AI Agents

Now we will build the three specialized agents that execute inside individual LangGraph nodes. Each agent is configured to run on `Gemini 3.1 Pro` and use structured outputs to communicate with the global graph.

Add the following to `app/services/graph_service.py`:

```python
# Initialize standard Gemini Model configurations
gemini_model = GeminiModel(
    'gemini-3.1-pro',
    api_key=os.environ.get("GEMINI_API_KEY")
)

# Agent 1: The Research Specialist
research_agent = Agent(
    model=gemini_model,
    result_type=ResearchNodeOutput,
    system_prompt="""
You are an expert research librarian. Your role is to ingest a technical topic, extract the core technical facts, 
and identify the relevant APIs. Omit fluff or marketing hype; extract pure, grounded data.
"""
)

# Agent 2: The Technical Writer
# This agent outputs a raw string (the Markdown draft), so we do not enforce structured results.
writer_agent = Agent(
    model=gemini_model,
    system_prompt="""
You are a senior technical writer. Your role is to take a set of researched technical facts and APIs, 
and expand them into a comprehensive, beautifully structured Markdown blog post.
Include clear headers, code block mockups where appropriate, and a professional tone.
"""
)

# Agent 3: The Editorial Auditor
editor_agent = Agent(
    model=gemini_model,
    result_type=EditorialAudit,
    system_prompt="""
You are a strict editorial director. Your role is to review technical blog drafts against corporate style rules.

Corporate Style Guidelines:
1. Must contain clear markdown headers.
2. Must include at least one technical code snippet or architectural diagram.
3. Must explain performance or cost characteristics of the proposed tech.

If the draft violates *any* of these, set 'approved=False' and compile precise revision instructions.
"""
)
```

---

## 🏗️ Assembling the Multi-Step StateGraph in LangGraph

Now we will write our LangGraph node execution functions, construct the transitions, add a **Conditional Edge** to evaluate the editor's audit, compile the graph, and execute the multi-turn loop.

Add the final assembly block in `app/services/graph_service.py`:

```python
# --- 3. Define LangGraph Node Functions ---

async def research_node(state: ContentWorkflowState) -> ContentWorkflowState:
    """Executes the Pydantic AI Research Agent and stores the structured output in state."""
    print("[Node: Researching] Compiling facts for topic:", state["topic"])
    
    # Execute the Pydantic AI agent loop
    result = await research_agent.run(
        user_prompt=f"Perform deep technical research on: {state['topic']}"
    )
    
    # Update global state safely
    state["research_data"] = result.data
    return state

async def drafting_node(state: ContentWorkflowState) -> ContentWorkflowState:
    """Executes the Writer Agent to compile raw Markdown text based on our state research."""
    print("[Node: Drafting] Compiling Markdown draft...")
    research_json = state["research_data"].model_dump_json(indent=2)
    
    writer_prompt = f"""
    Build a comprehensive blog post on the topic '{state['topic']}' using these verified facts:
    {research_json}
    """
    
    result = await writer_agent.run(user_prompt=writer_prompt)
    state["current_draft"] = result.data
    return state

async def auditing_node(state: ContentWorkflowState) -> ContentWorkflowState:
    """Executes the Pydantic AI Editor Agent to validate formatting guidelines."""
    print("[Node: Auditing] Evaluating draft compliance...")
    
    editor_prompt = f"""
    Review this draft for publication guidelines:
    
    {state['current_draft']}
    """
    
    result = await editor_agent.run(user_prompt=editor_prompt)
    state["audit_report"] = result.data
    state["iteration_count"] += 1
    return state

# --- 4. Define the Conditional Routing Logic ---

def should_continue(state: ContentWorkflowState) -> str:
    """Evaluates the Editor's audit report to determine stateflow routing."""
    audit: EditorialAudit = state["audit_report"]
    
    if audit.approved:
        print("[Router] Draft complies fully! Heading to publication.")
        return "complete"
    
    if state["iteration_count"] >= 3:
        print("[Router] Iteration limit (3) exceeded. Terminating to prevent loop locks.")
        return "complete"
        
    print(f"[Router] Redline flags detected: {audit.redline_issues}. Routing back to Research node.")
    return "revise"

# --- 5. Build and Compile the StateGraph ---

workflow = StateGraph(ContentWorkflowState)

# Register our nodes
workflow.add_node("research", research_node)
workflow.add_node("drafting", drafting_node)
workflow.add_node("auditing", auditing_node)

# Set up transitions
workflow.add_edge(START, "research")
workflow.add_edge("research", "drafting")
workflow.add_edge("drafting", "auditing")

# Add the conditional edge branching off the auditing node
workflow.add_conditional_edges(
    "auditing",
    should_continue,
    {
        "revise": "research",  # Cycle back if audit failed
        "complete": END       # Terminate if approved or iteration limit hit
    }
)

# Compile our graph into an executable stateflow machine
compiled_graph = workflow.compile()
```

---

## 🌐 Setting up the FastAPI Microservice Interface

Now let's build `app/main.py` to serve our multi-step agent flow asynchronously, returning the complete, audited draft and history in a single response payload.

```python
import time
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from app.services.graph_service import compiled_graph

app = FastAPI(
    title="Multi-Step Agentic Content Engine",
    description="Stateful multi-turn agent orchestration using LangGraph, Pydantic AI, and Gemini 3.1 Pro",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict strictly!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerationRequest(BaseModel):
    topic: str = Field(min_length=10, description="The technical topic to compile research and drafts for.")

class WorkflowResult(BaseModel):
    processing_time_ms: int
    final_state: dict

@app.post(
    "/api/v1/generate-content",
    response_model=WorkflowResult,
    status_code=status.HTTP_200_OK,
    summary="Trigger the stateful, multi-step content compilation graph"
)
async def generate_content_workflow(payload: GenerationRequest):
    """
    Triggers the compiled StateGraph. Coordinates transitions across Research, Drafting, 
    and Auditing nodes, executing Pydantic AI reasoning loops in parallel, and returns the final approved draft.
    """
    start_time = time.time()
    
    # Initialize the default global workflow state
    initial_state = {
        "topic": payload.topic,
        "research_data": None,
        "current_draft": None,
        "audit_report": None,
        "iteration_count": 0
    }
    
    try:
        # Run the graph using async call
        final_state = await compiled_graph.ainvoke(initial_state)
        duration_ms = int((time.time() - start_time) * 1000)
        
        return WorkflowResult(
            processing_time_ms=duration_ms,
            final_state=final_state
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stateful workflow execution aborted: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    # Local development server
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

---

## 🔒 Enterprise Scaling: Human-in-the-Loop & State Rollback

When scaling LangGraph systems in enterprise environments, take advantage of its advanced architectural features:

1.  **Human-in-the-Loop (Interrupts):** In corporate publishing pipelines, you shouldn't let an AI automatically publish drafts. LangGraph makes it incredibly easy to insert an `interrupt_before` hook on a node. When reached, the graph pauses execution, persists its current state statefully to a database, and waits for a human editor to review the redlines and press "resume" before continuing.
2.  **State Persistence & Time Travel:** LangGraph features built-in checkpointers (e.g., using PostgreSQL/Redis). This preserves a historical log of every single state transition. If an editor wants to revert to an older draft or re-run a generation path from step 2, they can "time travel" directly back to that specific historical transaction block.
3.  **Optimize Network Context with Prompt Caching:** Because the Research, Write, and Edit nodes process the exact same developing draft repeatedly, ensure your API endpoints are utilizing **Gemini 3.1 Pro's Context Caching** capabilities. By caching the global draft context, you cut your API pricing by up to 90% per loop iteration.

---

## 🚀 Running and Testing your Multi-Step Engine

Execute your application server locally:

```bash
# Start your FastAPI application using uv virtualized execution
uv run uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` to test the API with your custom content prompts.

### Sandbox Testing Input
Post this payload to the `/api/v1/generate-content` route:

```json
{
  "topic": "Google Gemini 3.1 Pro Context Caching API features and pricing"
}
```

The system will execute:
1.  **Research Node:** Compiles technical facts about Gemini 3.1 context caching (like the 32K token minimum, 90% input cost discount, and explicit resource management).
2.  **Drafting Node:** Compiles a Markdown article based on these facts.
3.  **Auditing Node:** Audits the draft. If the draft lacks a code block or cost explanation, it flags the issue (`approved=False`), details the revision rules, and cycles back to research.
4.  **Re-run:** The Research/Drafting nodes run again using the revision feedback.
5.  **Completion:** Once the Editor approves the draft, the router terminates the pipeline (`END`) and FastAPI returns the fully polished, compliant Markdown blog post.

*Are you building multi-step agent loops? Let's discuss state management systems, checkpointing databases, and workflow optimization in the comments below!*
