---
layout: post
title: "Deterministic Agentic Workflows: How to Build Zero-Failure Production Pipelines with PydanticAI and State Guards"
description: "A battle-tested engineering blueprint for eliminating non-deterministic hallucinations in autonomous AI agents using PydanticAI, typed dependency injection, finite state machine validation, and ModelRetry guardrails."
date: 2026-10-12 09:00:00 +0000
image: assets/images/deterministic-agents-pydanticai.webp
categories:
  - AI Agents & Autonomous Systems
tags:
  - PydanticAI
  - Python
  - AI Agents
  - System Design
  - DevOps
keywords: "deterministic ai agents pydanticai, zero failure agentic pipelines, type safe llm guardrails, structured output validation pydantic, production ai agent state machines, pydanticai modelretry"
faqs:
  - question: "Why do standard LangChain or raw prompt agents fail in production?"
    answer: "Raw prompt agents rely on probabilistic natural language parsing. When an LLM slightly alters JSON keys, emits unescaped quotes, or hallucinates data types, downstream database operations fail silently or trigger catastrophic HTTP 500 runtime exceptions."
  - question: "How does PydanticAI enforce type-safe execution and determinism?"
    answer: "PydanticAI compiles validation schemas directly from Python type hints. If a model output violates schema constraints or business rules, the framework automatically intercepts the error, serializes the exact validation diff into a corrective prompt turn, and re-invokes the model until an invariant-compliant object is produced."
  - question: "How does typed dependency injection work in PydanticAI?"
    answer: "Instead of relying on fragile global variables or unmanaged singletons, PydanticAI allows injecting typed dependency containers via RunContext[T]. This isolates database sessions, Redis caches, and API clients, enabling effortless unit testing with mock services."
---

Autonomous AI agents that fail 15% of the time may impress on social media demos. In production enterprise software, an agent with an 85% success rate is **completely unusable**.

When autonomous agents are granted write access to customer relational databases, authorized to issue financial refunds, or empowered to reconfigure cloud infrastructure, **non-deterministic behavior is an unacceptable liability**.

Traditional software engineering relies on strict contracts: a function receives typed inputs and guarantees typed, validated outputs. Large language models, by contrast, are fundamentally probabilistic token predictors.

To deploy agentic workflows safely in high-stakes environments, engineering teams must bridge this divide using **PydanticAI**, **Typed Dependency Injection**, and **Finite State Guards**.

This guide provides a comprehensive production blueprint for building zero-failure, deterministic agentic pipelines.

---

## 1. The Core Architectural Philosophy: Invariants Over Prompts

A common architectural flaw is attempting to force determinism through verbose system prompt warnings:
> *"IMPORTANT: Never issue a refund exceeding $500, always return valid ISO dates, and never leave transaction_id empty!"*

Under adversarial inputs, ambiguous user prompts, or edge-case context shifts, prompt-based constraints inevitably fail.

In a **Deterministic Agentic Architecture**, business policies are enforced as **immutable Python code invariants**. The LLM is treated as a probabilistic reasoning engine operating inside a rigid, type-safe sandbox:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PROBABILISTIC LLM LAYER (Gemini 2.5 Flash / Claude 3.5 Sonnet)                         │
│ Evaluates natural language user request, determines intent, proposes parameters       │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │ Emits JSON Payload
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ DETERMINISTIC COMPILED GUARDRAIL LAYER (PydanticAI Runtime)                            │
│ 1. Syntactic Validation: JSON types, regex matching, non-null fields                   │
│ 2. Semantic Validation: Relational logic (@model_validator)                            │
│ 3. External State Validation: Injected DB lookup via RunContext                        │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                         ┌─────────────────┴─────────────────┐
                         │ Validation Passed?                │
                         ├─────────────────┬─────────────────┤
                         │ NO              │ YES             │
                         ▼                 ▼                 ▼
          ┌───────────────────────────┐  ┌──────────────────────────────────────────────┐
          │ ModelRetry Feedback Loop  │  │ Execute Safe Database Mutation               │
          │ Re-prompts LLM with error │  │ (Zero risk of SQL or business logic failure) │
          │ traceback (Max 2 retries) │  └──────────────────────────────────────────────┘
          └──────────────┬────────────┘
                         │
                         └──────────────► Re-evaluates LLM
```

---

## 2. Defining Typed Domain Invariants with Pydantic

We define domain models that make invalid states mathematically impossible to represent:

```python
from enum import Enum
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, model_validator
import re

class RefundDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"

class RefundApprovalPayload(BaseModel):
    transaction_id: str = Field(..., description="Stripe transaction ID prefixed with txn_")
    customer_id: str = Field(..., description="Customer UUID prefixed with cust_")
    amount_usd: Decimal = Field(..., gt=Decimal("0.00"), le=Decimal("500.00"), description="Refund amount capped at $500")
    decision: RefundDecision
    policy_citation: str = Field(..., min_length=20, description="Verbatim citation from merchant refund policy")
    compliance_rationale: str = Field(..., min_length=30, description="Auditable reasoning for decision")

    @field_validator("transaction_id")
    @classmethod
    def validate_txn_format(cls, v: str) -> str:
        if not re.match(r"^txn_[a-zA-Z0-9]{16,24}$", v.strip()):
            raise ValueError(f"Transaction ID '{v}' does not match official Stripe pattern '^txn_[a-zA-Z0-9]{{16,24}}$'.")
        return v.strip()

    @field_validator("customer_id")
    @classmethod
    def validate_cust_format(cls, v: str) -> str:
        if not re.match(r"^cust_[a-zA-Z0-9]{12,18}$", v.strip()):
            raise ValueError(f"Customer ID '{v}' does not match official pattern '^cust_[a-zA-Z0-9]{{12,18}}$'.")
        return v.strip()

    @model_validator(mode="after")
    def verify_financial_invariants(self):
        # Invariant: If amount exceeds $300, decision CANNOT be APPROVED autonomously
        if self.amount_usd > Decimal("300.00") and self.decision == RefundDecision.APPROVED:
            raise ValueError(
                f"Policy Invariant Violation: Refunds over $300.00 (${self.amount_usd}) "
                f"require human compliance sign-off. Decision must be 'ESCALATE_TO_HUMAN'."
            )
        return self
```

---

## 3. Typed Dependency Injection with `RunContext`

Production agents should never import global database connections or environment variables directly. Global handles introduce race conditions and make automated unit testing impossible.

Using PydanticAI's `RunContext[Deps]`, we inject database sessions, fraud detection clients, and user identities into the agent cleanly:

```python
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext, ModelRetry

@dataclass
class EnterpriseDependencies:
    db_session: any            # PostgreSQL / SQLAlchemy session
    fraud_score_service: any   # External fraud scoring API client
    operator_role: str         # "TIER_1_SUPPORT" or "SUPERVISOR"

# Initialize Agent with typed dependency constraints
compliance_agent = Agent(
    "google-gla:gemini-2.5-flash",
    deps_type=EnterpriseDependencies,
    result_type=RefundApprovalPayload,
    retries=2,  # Up to 2 self-healing retry turns
    system_prompt="""
You are the Senior Compliance and Financial Settlement Agent.
Your objective is to evaluate customer refund requests strictly against merchant policy.

RULES:
1. Always verify the transaction ID in the database using your tool before making a decision.
2. Refunds over $300 must be marked ESCALATE_TO_HUMAN.
3. If fraud risk exceeds 0.70, reject the request immediately.
"""
)
```

---

## 4. Guarded Tool Execution with `ModelRetry`

If an agent attempts to query a non-existent database record or passes corrupt parameters to an internal API, do not let Python throw an unhandled exception. 

Raise `ModelRetry` directly inside the tool to explain the operational error to the LLM and let it self-correct:

```python
@compliance_agent.tool
def lookup_transaction_record(
    ctx: RunContext[EnterpriseDependencies],
    transaction_id: str
) -> dict:
    """Verifies that the transaction exists in the database and retrieves billing details."""
    
    # Query database via injected dependency
    # Simulated database lookup
    if transaction_id == "txn_invalid_0000000000":
        # Raise ModelRetry to instruct the LLM on how to recover!
        raise ModelRetry(
            f"Database Error: Transaction '{transaction_id}' was not found in the settlements table. "
            "Re-check the customer transcript for the correct transaction ID."
        )

    return {
        "transaction_id": transaction_id,
        "amount_billed": "149.00",
        "currency": "USD",
        "settled_at": "2026-10-08",
        "fraud_risk_score": 0.12
    }
```

---

## 5. End-to-End Execution & Self-Healing Verification

Below is an execution script demonstrating how the agent catches an invalid input and recovers deterministically:

```python
import asyncio
from decimal import Decimal

async def main():
    deps = EnterpriseDependencies(
        db_session=None,
        fraud_score_service=None,
        operator_role="TIER_1_SUPPORT"
    )

    customer_ticket = (
        "Customer cust_992817261524 reported double-billing on order txn_1a2b3c4d5e6f7g8h9i0j. "
        "The charge was for $149.00. Customer is within the 14-day refund window. Please process full refund."
    )

    print("🤖 Processing customer refund request with deterministic guardrails...")
    result = await compliance_agent.run(customer_ticket, deps=deps)

    print("\n✅ Validated, Invariant-Guaranteed Refund Approval:")
    print(result.data.model_dump_json(indent=2))

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 6. The 5 Rules for Deterministic Agent Systems

Before promoting an agent to write production database records:

1. **Never Accept Raw Strings**: Always wrap LLM outputs in strict Pydantic schemas with regex and range boundaries.
2. **Move Business Invariants into `@model_validator`**: Never rely on system prompts to enforce maximum refund amounts, chronological dates, or state transitions.
3. **Inject Dependencies Cleanly**: Use `RunContext` for all external services to enable deterministic unit testing with mock fixtures.
4. **Use `ModelRetry` for Self-Healing**: Catch runtime tool exceptions and guide the model back to valid inputs rather than returning HTTP 500 errors.
5. **Cap Retry Depth at 2**: If an agent cannot produce a valid payload in 2 retry attempts, terminate execution and route the task to a human operator.
