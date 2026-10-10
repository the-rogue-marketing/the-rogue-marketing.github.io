---
layout: post
title: "AI System Design Series (Part 6): Autonomous Agent Orchestration with PydanticAI for ERP and EHR Mutations"
description: "How to engineer type-safe, autonomous multi-turn agents that safely interact with mission-critical systems. Implementing PydanticAI for automated GL allocation in SAP/NetSuite and claim scrubbing in Epic/Cerner."
author: professor-xai
categories: [system-design, pydantic-ai, ai-agents, python]
image: assets/images/ai-system-design-part-6-pydantic-ai-agents.webp
featured: true
last_modified_at: 2026-10-10
keywords: "pydantic-ai agents, autonomous erp agent, rcm claim scrubbing agent, type safe tool calling, modelretry self healing, enterprise ai agents"
faq:
  - question: "Why is PydanticAI superior to general agent frameworks for enterprise mutations?"
    answer: "General agent frameworks often rely on unstructured string outputs and loosely typed JSON parsing. PydanticAI enforces strict, compile-time and runtime type safety using Pydantic schemas for tool arguments, dependency injection via RunContext, and structured return values. If an agent attempts to invoke a tool with malformed arguments, the framework automatically catches the error and prompts the model to self-heal using ModelRetry."
  - question: "What is the ModelRetry pattern in PydanticAI?"
    answer: "ModelRetry allows a validator or tool to raise an explicit exception that is fed directly back into the LLM's conversational scratchpad during the current execution turn. The model reads the exact error traceback and adjusts its parameters without crashing the server or failing the workflow."
  - question: "How do you guarantee idempotency when an agent mutates external ERP or EHR systems?"
    answer: "Every mutating tool must require a deterministic idempotency key derived from the document's SHA-256 hash and workflow ID. Before executing an external HTTP POST or database insert, the tool verifies whether the transaction has already succeeded, returning the existing transaction ID if repeated."
---

In Part 4 and Part 5 of this series, we equipped our architecture with high-precision contextual search (Hybrid pgvector and Knowledge Graphs) and rapid System-1 decision routing (TypeSafe AI's Jev).

When an invoice matches its purchase order perfectly, or a medical claim is 100% clean, Jev routes it straight to automated settlement in under 120 milliseconds.

However, in the real world, approximately 15% to 20% of enterprise documents contain complex discrepancies that cannot be resolved by a simple binary decision:
- An invoice line item has no purchase order reference and must be allocated to the correct General Ledger (GL) account code based on historical procurement patterns.
- An invoice has an unexplained $450 shipping surcharge that violates contract terms and requires drafting a formal vendor dispute notice.
- A healthcare claim is flagged with an NCCI (National Correct Coding Initiative) modifier conflict between CPT 99214 and CPT 11100, requiring a clinical coder agent to review physician notes and determine whether Modifier 25 is medically justified.

To resolve these nuanced exceptions, we need **Autonomous Multi-Turn Agents**.

However, in financial accounting and healthcare, deploying unconstrained agents is extraordinarily dangerous. If an agent hallucinates a debit transaction, calls an ERP endpoint with missing parameters, or modifies an Electronic Health Record (EHR) incorrectly, the consequences range from massive balance sheet reconciliation errors to severe regulatory penalties.

To make autonomous agents safe for production, we must build them on **PydanticAI**.

In this sixth installment of our AI System Design Series, we build the **Autonomous Agent Execution Layer**:

1. Why Unconstrained Agents Fail: The dangers of untyped tool-calling and parameter drift.
2. Architecture of PydanticAI: Dependency injection (`RunContext[T]`), type-safe tools, and `ModelRetry` self-healing loops.
3. Domain 1 (Accounts Payable): Building the Autonomous GL Allocator and Vendor Dispute Agent for SAP / NetSuite.
4. Domain 2 (Healthcare RCM): Building the Autonomous Claim Scrubber and Payer Appeal Agent for Epic / Cerner.
5. Idempotent Tool Design: Guaranteeing zero duplicate mutations across distributed systems.

## The Architecture of a Type-Safe Enterprise Agent

Most open-source agent frameworks treat tools as arbitrary Python functions that accept loose dictionaries and return unstructured strings. When an LLM generates arguments for an untyped tool, subtle hallucinations occur:
- An integer `account_code` is passed as a string `"001-4402-A"`.
- A currency amount `$142.50` is passed with a dollar sign rather than a clean float.
- A required enum `transaction_type` is passed as a synonym like `"credit_adjustment"` instead of the required `"REVERSAL"`.

PydanticAI eliminates these failure modes by enforcing strict Pydantic models across every component of the agent lifecycle:

```
[Agent Turn]
      |
      v
+-------------------------------------------------------+
| PydanticAI Agent Core (Gemini 3.8 Flash / Claude 3.7) |
| - System Prompt & Few-Shot Invariants                 |
| - Injected Dependencies: RunContext[EnterpriseContext] |
+---------------------------+---------------------------+
                            |
           +----------------+----------------+
           |                                 |
           v                                 v
+-------------------------+      +-------------------------+
| Tool: lookup_gl_history |      | Tool: post_erp_journal  |
| Args: Typed Pydantic    |      | Args: Strict GL Entry   |
+------------+------------+      +------------+------------+
             |                                |
             +----------------+---------------+
                              |
                              v
                  [Validation Assertion]
                  - Passes? --> Return Structured Result
                  - Fails?  --> Trigger ModelRetry Loop
```

### Key Architectural Primitives in PydanticAI

1. Strict Schema Binding: Every tool parameter is defined as a Pydantic model. If the model generates an invalid type, the parser intercepts the error before the function can execute.
2. Type-Safe Dependency Injection (`RunContext[T]`): The agent does not use global variables. Database connection pools, tenant credentials, and HTTP clients are passed type-safely into each tool execution context.
3. The `ModelRetry` Self-Healing Loop: When business logic fails inside a tool, rather than crashing the worker pod, the tool raises a `ModelRetry` exception containing the exact failure reason. The agent consumes this feedback and attempts an adjusted plan within the same session turn.

## Domain 1: Accounts Payable Autonomous GL Allocator

When an invoice arrives without a pre-existing Purchase Order, someone in accounting must determine which General Ledger (GL) account and cost center should be charged.

Let us build an autonomous GL Allocation Agent in PydanticAI:

```python
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, ModelRetry
from typing import List, Optional
from decimal import Decimal
import httpx

# Injected enterprise context
class ERPContext:
    tenant_id: str
    erp_session_token: str
    chart_of_accounts: List[str] # Valid GL codes e.g. ["6010-TRAVEL", "6020-SOFTWARE", "6030-OFFICE"]
    http_client: httpx.AsyncClient

# Structured outcome
class GLAllocationResult(BaseModel):
    invoice_number: str
    allocated_gl_code: str = Field(description="Selected General Ledger code from chart of accounts")
    cost_center: str
    tax_code: str
    justification_summary: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)

# Instantiate the PydanticAI Agent
gl_agent = Agent(
    "google-gla:gemini-3.8-flash",
    deps_type=ERPContext,
    result_type=GLAllocationResult,
    system_prompt=(
        "You are an autonomous senior accounts payable accountant. "
        "Your task is to analyze non-PO invoices, inspect historical vendor accounting entries, "
        "and allocate the invoice line items to the correct General Ledger (GL) account code. "
        "You must strictly verify that the GL code exists in the active chart of accounts."
    )
)

@gl_agent.tool
async def query_historical_vendor_allocations(
    ctx: RunContext[ERPContext], 
    vendor_tax_id: str
) -> List[dict]:
    # Query historical Silver lakehouse records for this vendor
    # Returns the last 5 GL accounts previously used for this supplier
    return [
        {"invoice": "INV-101", "gl_code": "6020-SOFTWARE", "description": "Cloud hosting renewal"},
        {"invoice": "INV-102", "gl_code": "6020-SOFTWARE", "description": "Database licenses"}
    ]

@gl_agent.tool
async def validate_and_reserve_gl_budget(
    ctx: RunContext[ERPContext], 
    gl_code: str, 
    amount: float
) -> str:
    # Verify that the GL code exists in the tenant chart of accounts
    if gl_code not in ctx.deps.chart_of_accounts:
        raise ModelRetry(
            f"Invalid GL code '{gl_code}'. It does not exist in the active chart of accounts. "
            f"Available accounts are: {ctx.deps.chart_of_accounts}. Please select a valid code."
        )
    
    # In production, inspect live SAP budget balance
    return f"Budget verified for {gl_code}. Remaining monthly balance: $45,000.00."
```

Notice the power of `ModelRetry`: If the model attempts to allocate an expense to `"6099-MISC"`, our tool catches the violation and prompts the LLM to pick an authorized account from the active chart of accounts. The agent self-corrects in real time without human intervention.

## Domain 2: Healthcare RCM Autonomous Claim Scrubber

In healthcare billing, modifier conflicts represent the #1 cause of outpatient commercial claim denials. 

For example, when a patient visits an endocrinologist for a routine office visit (CPT 99214) and also undergoes a skin biopsy (CPT 11100) during the same visit, Medicare and commercial payers will deny the office visit as an "unbundled duplicate" unless the physician documents that the evaluation was distinct and appends **Modifier 25**.

Let us build an autonomous Claim Scrubber Agent in PydanticAI that reviews clinical notes, checks NCCI edits, and attaches the appropriate billing modifier:

```python
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, ModelRetry
from typing import List, Optional

class RCMContext:
    ehr_api_url: str
    payer_id: str
    ncci_edit_rules: dict # Coding conflict rules
    http_client: httpx.AsyncClient

class ScrubbedClaimResult(BaseModel):
    claim_id: str
    modifications_applied: List[str]
    supporting_clinical_rationale: str
    ready_for_electronic_submission: bool
    requires_physician_signature: bool

rcm_scrubber_agent = Agent(
    "google-gla:gemini-3.8-flash",
    deps_type=RCMContext,
    result_type=ScrubbedClaimResult,
    system_prompt=(
        "You are an expert Certified Professional Coder (CPC) reviewing medical billing claims. "
        "Your objective is to inspect CPT procedure codes against NCCI unbundling edits, "
        "examine clinical progress notes, and append appropriate modifiers (such as Modifier 25 or 59) "
        "only when documented medical necessity strictly supports separate reimbursement."
    )
)

@rcm_scrubber_agent.tool
async def inspect_ncci_conflict(
    ctx: RunContext[RCMContext], 
    cpt_primary: str, 
    cpt_secondary: str
) -> dict:
    pair_key = f"{cpt_primary}-{cpt_secondary}"
    if pair_key in ctx.deps.ncci_edit_rules:
        return {
            "has_conflict": True,
            "rule": ctx.deps.ncci_edit_rules[pair_key],
            "modifier_allowed": True, # Modifier 25 permitted with clinical documentation
            "guideline": "Modifier 25 requires documentation of a significant, separately identifiable E/M service."
        }
    return {"has_conflict": False, "modifier_allowed": True}

@rcm_scrubber_agent.tool
async def fetch_physician_clinical_note(
    ctx: RunContext[RCMContext], 
    patient_id: str, 
    encounter_date: str
) -> str:
    # Retrieve raw clinical note text from EHR (Epic / Cerner)
    return (
        "Patient seen for follow-up of poorly controlled Type 2 Diabetes. Comprehensive exam conducted. "
        "Adjustment made to insulin glargine dosage. Additionally, patient presented a suspicious 8mm pigmented "
        "lesion on left shoulder. After discussion, performed punch biopsy under local anesthesia."
    )
```

When this agent executes:
1. It queries `inspect_ncci_conflict` and discovers that CPT 99214 and CPT 11100 conflict.
2. It calls `fetch_physician_clinical_note` and analyzes the physician's documented rationale.
3. It concludes that the diabetes management was distinct from the shoulder lesion biopsy.
4. It programmatically appends `Modifier 25` to CPT 99214, records the justification, and flags the claim as ready for electronic submission.

## Idempotency and Side-Effect Guards

The most critical operational rule when agents interact with production ERP and EHR databases is **Idempotency**.

What happens if an agent successfully invokes `post_invoice_to_sap()`, but the network connection drops before the LLM receives the response? If the agent retries the call, it risks posting a duplicate debit entry to the ledger.

Every mutating tool must enforce a deterministic idempotency token:

```python
import redis.asyncio as redis

@gl_agent.tool
async def post_gl_journal_entry(
    ctx: RunContext[ERPContext], 
    invoice_number: str, 
    gl_code: str, 
    amount: float
) -> str:
    idempotency_key = f"erp_lock:{ctx.deps.tenant_id}:{invoice_number}"
    
    # 1. Check if this exact transaction was already committed
    existing_tx = await redis_client.get(idempotency_key)
    if existing_tx:
        return f"Transaction previously completed. Existing ERP Transaction ID: {existing_tx.decode('utf-8')}"

    # 2. Acquire atomic distributed lock
    acquired = await redis_client.set(f"lock:{idempotency_key}", "locked", nx=True, ex=30)
    if not acquired:
        raise ModelRetry("Concurrent mutation in progress for this invoice. Please wait 5 seconds and retry.")

    try:
        # 3. Execute external HTTP mutation to SAP / NetSuite
        tx_id = await execute_sap_post(gl_code, amount, invoice_number)
        
        # 4. Record permanent idempotency record
        await redis_client.set(idempotency_key, tx_id, ex=86400 * 30)
        return f"Successfully created ERP journal entry. Transaction ID: {tx_id}"
    finally:
        await redis_client.delete(f"lock:{idempotency_key}")
```

## Summary and What Comes Next

In this sixth installment, we built the autonomous agent execution layer:
- Demonstrated why untyped agent frameworks cause severe parameter drift in enterprise environments.
- Implemented PydanticAI to enforce compile-time and runtime type safety across tools and dependency injection.
- Utilized `ModelRetry` to allow agents to dynamically self-correct schema errors and business rule violations without human intervention.
- Constructed real-world agents for Accounts Payable GL allocation and Healthcare RCM claim scrubbing.
- Enforced cryptographic idempotency locks to guarantee zero duplicate financial or clinical mutations.

However, even the best autonomous agents should not operate with 100% unilateral authority. High-value invoices and complex clinical denials still require human oversight. Furthermore, when a human corrects an agent, how does the system learn from that feedback?

In Part 7 of this series, we will build the Human-in-the-Loop (HITL) and Active Learning Flywheel: utilizing Temporal Signals to pause and resume workflows, and storing human corrections in an active exemplar memory store so our agents continuously improve.
