---
layout: post
title: 'AI System Design Series (Part 8): Bi-Temporal Audit Trails, Multi-Tenancy,
  and HIPAA/SOC-2 Data Isolation'
description: How to engineer immutable regulatory audit trails and cryptographic multi-tenancy.
  Implementing bi-temporal modeling, Iceberg snapshot time-travel, pgvector Row-Level
  Security, and model provenance logging.
author: professor-xai
categories: [System Design & Scalability]
image: assets/images/ai-system-design-part-8-security-auditability.webp
featured: true
last_modified_at: 2026-10-10
keywords: bi temporal data modeling, ai audit trail architecture, hipaa soc 2 ai compliance,
  pgvector row level security, model provenance tracking, iceberg time travel
faq:
- {question: 'What is bi-temporal data modeling and why is it mandatory for enterprise
    AI?', answer: 'Bi-temporal data modeling tracks two separate timelines for every
    record: Valid Time (when an event occurred in the real world, such as an invoice
    issue date) and Transaction Time (when the record was written to the system).
    This allows auditors to reconstruct exactly what the system knew at any specific
    point in history, which is legally required under SOX and Medicare guidelines.'}
- {question: 'How do you enforce multi-tenant isolation in pgvector semantic search?',
  answer: 'You implement PostgreSQL Row-Level Security (RLS) coupled with session-scoped
    connection variables (e.g., SET LOCAL app.current_tenant_id = ''tenant_123'').
    This guarantees that vector similarity queries and full-text searches physically
    cannot retrieve document chunks belonging to other corporate subsidiaries or healthcare
    clinics.'}
- {question: 'What constitutes complete AI Model Provenance in an audit trail?', answer: 'A
    complete AI model provenance record captures the cryptographic SHA-256 hash of
    the input document, the exact foundation model version (e.g. gemini-3.8-flash-001),
    temperature setting, system prompt template hash, Jev calibrated confidence score,
    and the exact list of RAG evidence chunk IDs retrieved during execution.'}
tags: [AI Agents, OCR & Vision, PydanticAI, Security, System Design]
---
In Parts 6 and 7 of this series, we developed the autonomous agent execution layer using PydanticAI and engineered durable human-in-the-loop workflows with an active learning feedback loop.

At this stage, our system extracts documents, verifies them against domain ontologies, routes them via System-1 models, and executes automated transactions.

However, in financial accounting and healthcare, technical capability is meaningless if your system cannot survive a **statutory compliance audit**.

Consider these real-world enterprise scenarios:
- Sarbanes-Oxley (SOX) & IRS Audit: Three years from now, external auditors inspect Invoice #88412. They ask: *"Why was this invoice approved with an unbilled variance on October 10, 2026? Who authorized the transaction, which model extracted it, and what vendor contract was in effect on that exact day?"*
- HIPAA & Medicare OIG Audit: Federal regulators inspect an electronic claim submission. They ask: *"Why was this surgical procedure coded as CPT 29881? Was Protected Health Information (PHI) leaked to an unauthorized model provider? How do you mathematically prove that Clinic A's patient charts were never accessible by Clinic B during semantic search?"*

If your architecture relies on a single relational table with basic `created_at` and `updated_at` timestamps, you will fail your audit.

In regulated enterprise systems, **data is bi-temporal, immutable, and strictly partitioned**.

In this eighth installment of our AI System Design Series, we build the **Security, Multi-Tenancy, and Auditability Framework**:

1. Bi-Temporal Data Architecture: Valid Time versus Transaction Time.
2. Apache Iceberg Time-Travel: Querying historical states for statutory audits.
3. Cryptographic AI Model Provenance: Logging the complete forensic chain of custody for every AI decision.
4. Hard Multi-Tenancy: Enforcing Row-Level Security (RLS) in PostgreSQL and `pgvector`.
5. Zero-Data-Retention Pipelines: Local PII/PHI redaction to satisfy HIPAA and SOC-2 Type II controls.

## The Bi-Temporal Data Architecture

In traditional CRUD applications, when a record is updated, the previous state is overwritten or moved to an archive table.

In enterprise finance and healthcare, **overwriting state is forbidden**. You must capture two independent dimensions of time:

```
+-----------------------------------------------------------------------+
|                       BI-TEMPORAL TIMELINES                           |
+-----------------------------------------------------------------------+
| 1. Valid Time (Business Time): When the event occurred in reality     |
|    - e.g. Patient received treatment on 2026-04-12                    |
|    - e.g. Vendor issued invoice on 2026-05-01                         |
+-----------------------------------------------------------------------+
| 2. Transaction Time (System Time): When the database recorded it      |
|    - e.g. Ingestion worker committed record on 2026-05-03 14:22:01    |
|    - e.g. Auditor reviews record on 2026-10-10                        |
+-----------------------------------------------------------------------+
```

Why does this distinction matter?

Suppose an insurance company amends its reimbursement policy for CPT 99214 on June 1st, backdating the policy retroactively to April 1st. 
If an auditor inspects a claim processed on May 15th, you must be able to ask:
*"What was the exact state of our payer policy knowledge base as of May 15th, regardless of subsequent retroactive amendments?"*

### Implementing Bi-Temporal Iceberg Tables

Apache Iceberg natively supports transaction-time snapshots through its immutable manifest tree. We structure our Silver and Gold lakehouse tables with explicit bi-temporal bounds:

```sql
CREATE TABLE silver_rcm.adjudicated_claims (
    claim_id VARCHAR(64) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL,
    patient_identifier VARCHAR(64) NOT NULL,
    
    -- Valid Time (When the clinical care occurred)
    valid_from_date DATE NOT NULL,
    valid_to_date DATE NOT NULL,
    
    -- Financial Payload
    primary_cpt_code VARCHAR(16) NOT NULL,
    total_charge_amount DECIMAL(12, 2) NOT NULL,
    adjudication_status VARCHAR(32) NOT NULL,
    
    -- AI Forensic Provenance Hash
    model_provenance_id UUID NOT NULL,
    
    -- Transaction Time (Managed automatically by Iceberg snapshot commits)
    system_ingested_at TIMESTAMP WITH TIME ZONE NOT NULL
);
```

When an auditor arrives in 2029, we do not guess what happened. We execute an Iceberg time-travel query against the historical snapshot:

```sql
-- Query the exact state of the claims table as it existed on Oct 10, 2026
SELECT claim_id, primary_cpt_code, adjudication_status 
FROM silver_rcm.adjudicated_claims 
FOR SYSTEM_TIME AS OF '2026-10-10 08:00:00 UTC'
WHERE tenant_id = 'clinic_north_east';
```

The lakehouse reads the historical manifest snapshot directly from S3 metadata, reconstructing the exact records with zero data corruption.

## Cryptographic AI Model Provenance

When an autonomous agent generates a decision, you must log the complete **Chain of Custody**. 

If a claim is audited, you cannot simply say *"Gemini processed it."* You must record:
1. Input Document Binary: SHA-256 hash of the exact scanned file.
2. Model Architecture: Exact model tag (`gemini-3.8-flash-001`), temperature, and decoding parameters.
3. System-1 Triage: Jev calibrated confidence score and verdict enum.
4. RAG Context Hash: Cryptographic hashes of the exact policy chunks retrieved from the knowledge base.
5. Injected Invariants: Hash of the active chart of accounts or NCCI coding rules.
6. Execution Traceback: Step-by-step tool invocation trajectory.

### The Provenance Log Schema

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List
import hashlib
import json

class AIModelProvenanceRecord(BaseModel):
    provenance_id: str
    tenant_id: str
    document_sha256: str
    
    # Model Configuration
    extraction_model: str = Field(default="gemini-3.8-flash")
    model_temperature: float = Field(default=0.0)
    system_prompt_sha256: str
    
    # System-1 Triage Provenance
    jev_decision_model: str = Field(default="typesafe/jev-latest")
    jev_confidence_score: float
    jev_verdict: str
    
    # Context Evidence Provenance
    retrieved_chunk_ids: List[str]
    context_corpus_hash: str
    
    # Execution Metadata
    executed_tool_calls: List[str]
    human_override_occurred: bool
    final_output_sha256: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

def create_provenance_record(
    tenant_id: str,
    raw_document_bytes: bytes,
    system_prompt: str,
    jev_eval: dict,
    rag_chunks: List[dict],
    tool_history: List[str],
    final_output: dict
) -> AIModelProvenanceRecord:
    doc_hash = hashlib.sha256(raw_document_bytes).hexdigest()
    prompt_hash = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()
    
    # Create deterministic hash of retrieved evidence
    chunk_ids = [c["chunk_id"] for c in rag_chunks]
    corpus_text = "".join(sorted([c["chunk_content"] for c in rag_chunks]))
    corpus_hash = hashlib.sha256(corpus_text.encode("utf-8")).hexdigest()
    
    out_hash = hashlib.sha256(json.dumps(final_output, sort_keys=True).encode("utf-8")).hexdigest()

    return AIModelProvenanceRecord(
        provenance_id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        document_sha256=doc_hash,
        system_prompt_sha256=prompt_hash,
        jev_confidence_score=jev_eval["confidence_score"],
        jev_verdict=jev_eval["verdict"],
        retrieved_chunk_ids=chunk_ids,
        context_corpus_hash=corpus_hash,
        executed_tool_calls=tool_history,
        human_override_occurred=False,
        final_output_sha256=out_hash
    )
```

This provenance record is saved to an immutable, append-only audit table. In the event of litigation or a regulatory investigation, you possess cryptographic proof that the AI operated strictly within approved policies.

## Multi-Tenancy and Cryptographic Data Isolation

In enterprise SaaS, multi-tenancy cannot rely on application-level `WHERE tenant_id = 'xxx'` clauses in raw SQL strings. A developer forgetting a single `WHERE` clause will leak confidential vendor contracts or patient medical records across organizations.

We enforce multi-tenancy at the **database engine level** using **PostgreSQL Row-Level Security (RLS)**.

### Enforcing Row-Level Security in PostgreSQL & pgvector

```sql
-- 1. Enable RLS on policy chunks and extracted documents
ALTER TABLE policy_knowledge_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE silver_finance.canonical_invoices ENABLE ROW LEVEL SECURITY;

-- 2. Create the Tenant Isolation Policy
-- Users can only SELECT or INSERT records matching their active session tenant
CREATE POLICY tenant_isolation_policy ON policy_knowledge_chunks
    AS RESTRICTIVE
    USING (tenant_id = current_setting('app.current_tenant_id', true));

CREATE POLICY tenant_invoice_policy ON silver_finance.canonical_invoices
    AS RESTRICTIVE
    USING (tenant_id = current_setting('app.current_tenant_id', true));
```

### Application Connection Pool Integration

When a worker pod executes a query, it sets the session variable within an atomic transaction block:

```python
import asyncpg

async def execute_isolated_tenant_query(
    pool: asyncpg.Pool, 
    tenant_id: str, 
    query_vector: list
) -> list:
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Bind the session to the tenant
            await conn.execute("SET LOCAL app.current_tenant_id = $1;", tenant_id)
            
            # Execute vector search
            # PostgreSQL RLS automatically filters out all chunks from other tenants
            rows = await conn.fetch("""
                SELECT chunk_id, chunk_content
                FROM policy_knowledge_chunks
                ORDER BY dense_embedding <=> $1::vector
                LIMIT 5;
            """, query_vector)
            
            return rows
```

Even if an injection attack compromises the application layer or an engineer writes an unconstrained `SELECT * FROM policy_knowledge_chunks`, the PostgreSQL kernel physically prevents data from leaking across tenant perimeters.

## Zero-Data-Retention and PHI Redaction

When integrating with third-party foundation models like Gemini 3.8 Flash, compliance frameworks (HIPAA BAA and SOC-2 Type II) demand strict data privacy controls:

1. Enterprise BAA (Business Associate Agreement): You must execute an enterprise agreement ensuring that model inputs and outputs are never logged or used for model training.
2. In-Line PII/PHI Redaction: Sensitive identifiers (Social Security Numbers, patient home addresses, driver's licenses) that are not strictly necessary for billing adjudication should be scrubbed before sending payloads over external networks.

We integrate **Microsoft Presidio** inside our ingestion worker to redact direct identifiers:

```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

def scrub_patient_phi(clinical_text: str) -> str:
    # Analyze text for HIPAA 18 Safe Harbor identifiers
    results = analyzer.analyze(
        text=clinical_text,
        entities=["US_SSN", "PHONE_NUMBER", "EMAIL_ADDRESS", "US_PASSPORT"],
        language="en"
    )
    
    # Replace identifiers with cryptographic placeholder tokens
    anonymized = anonymizer.anonymize(
        text=clinical_text,
        analyzer_results=results
    )
    return anonymized.text
```

## Summary and What Comes Next

In this eighth installment, we hardened our platform for statutory enterprise compliance:
- Modeled data bi-temporally, separating Valid Time from Transaction Time.
- Implemented Apache Iceberg snapshot time-travel to reproduce historical table states years later.
- Architected Cryptographic AI Model Provenance, capturing the end-to-end chain of custody for every AI turn.
- Enforced PostgreSQL Row-Level Security (RLS) to guarantee strict multi-tenant isolation across pgvector searches.
- Deployed in-line PHI sanitization to satisfy HIPAA and SOC-2 Type II controls.

Now our platform is secure, audit-proof, and compliant. But how do we handle external regulatory drift when Medicare updates CPT codes or European tax authorities update VAT rules? And how do we test our system before deploying to production?

In Part 9 of this series, we will build the Regulatory Schema Drift Engine and Synthetic Backtesting Simulator: handling quarterly NCCI code updates and stress-testing our PydanticAI agents with synthetic fuzzed claims.
