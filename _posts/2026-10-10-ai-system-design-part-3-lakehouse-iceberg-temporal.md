---
layout: post
title: "AI System Design Series (Part 3): The Medallion Data Lakehouse, Apache Iceberg, and Temporal DAG Workflows"
description: "How to engineer durable data pipelines for unstructured AI document workloads. Structuring Bronze, Silver, and Gold layers with Apache Iceberg, and orchestrating resilient DAGs using Temporal."
author: professor-xai
categories: [system-design, data-engineering, python, temporal]
image: assets/images/ai-system-design-part-3-lakehouse.webp
featured: true
last_modified_at: 2026-10-10
keywords: "medallion architecture ai, apache iceberg python, temporal workflow document processing, dag orchestration enterprise, data lakehouse parquet, durable execution temporal"
faq:
  - question: "Why use the Medallion Architecture for document AI systems?"
    answer: "The Medallion Architecture separates storage into Bronze (immutable raw files and initial LLM extractions), Silver (validated, standardized Common Data Models), and Gold (aggregated business marts). This separation prevents analytical queries from degrading transactional extraction, and allows reprocessing historical documents whenever downstream business logic evolves."
  - question: "Why choose Apache Iceberg over standard Parquet files on S3?"
    answer: "Raw Parquet files lack ACID transactions, table-level concurrency control, and schema evolution. Apache Iceberg provides transactional snapshot isolation, hidden partitioning, and historical time-travel queries, which are essential for regulatory compliance and audit trails."
  - question: "How does Temporal differ from Celery or Airflow for document orchestration?"
    answer: "Airflow is designed for scheduled batch ETL, and Celery is stateless task-based without durable state tracking. Temporal provides durable execution: workflows can sleep for days awaiting human approval or retry transient API failures without losing local variable state or holding open database connections."
---

In Part 1 and Part 2 of this series, we solved two major technical challenges:
1. Distributed document ingestion using Kafka and Gemini 3.8 Flash.
2. Canonical semantic modeling using Pydantic, PEPPOL BIS 3.0 for financial invoices, and HL7 FHIR for healthcare claims.

Now we face a core data engineering challenge: Where and how do we persist this data at enterprise scale?

In an enterprise processing 100,000 documents per day, writing every extracted entity directly into an operational PostgreSQL database creates severe bottlenecks. 

Relational databases excel at row-level transactional lookups (OLTP), but they degrade rapidly when handling petabyte-scale historical document archives, complex analytical aggregations, and high-dimensional semantic search indexing. Furthermore, if you only store the final parsed record, you lose the ability to re-extract documents when you update your AI models in the future.

To build a resilient enterprise platform, you must structure your storage as a Medallion Data Lakehouse powered by Apache Iceberg, orchestrated by durable Directed Acyclic Graphs (DAGs) using Temporal.

In this third installment of our AI System Design Series, we will cover:

1. The Medallion Architecture for Document Intelligence: Bronze, Silver, and Gold storage tiers.
2. Apache Iceberg in Production: ACID transactions, schema evolution, and time-travel querying.
3. Durable Orchestration with Temporal: Replacing fragile Celery tasks with durable execution workflows.
4. Implementing the Sagas Pattern: Reversing partial ERP allocations and claim submissions upon failure.

## The Medallion Architecture for Unstructured Document Intelligence

The Medallion Architecture organizes your data lakehouse into three distinct tiers of data quality and refinement:

### Bronze Tier: Raw Ingestion and Extraction Dumps
The Bronze layer is an append-only, immutable record of reality. It stores:
- The raw binary document (PDF, TIFF, JPEG).
- The raw, unadulterated JSON response directly from the Gemini 3.8 Flash extraction model.
- Extraction metadata: model version, token consumption, extraction timestamp, and raw prompt parameters.

Why is the Bronze layer critical? Because AI models improve constantly. If Google releases a superior model or your team refines its extraction prompt in six months, you can re-run extraction over your entire historical Bronze archive without asking customers to re-upload documents.

### Silver Tier: Cleaned, Validated Common Data Models
The Silver layer contains our canonical domain entities:
- PEPPOL BIS 3.0 Invoices (Accounts Payable).
- HL7 FHIR Claims (Healthcare RCM).

Data enters the Silver layer only after passing the strict Pydantic validation rules we established in Part 2. Calculations have been verified, provider NPI numbers have passed Luhn checksums, and tax line items have balanced. The Silver layer is deduplicated, enriched with master vendor records, and stored in columnar Apache Iceberg tables.

### Gold Tier: Business Aggregations and Financial Marts
The Gold layer powers executive dashboards, cash-flow forecasting, fraud analytics, and RCM denial telemetry:
- Accounts Payable: Daily vendor liabilities, early-payment discount opportunities, and unbilled purchase order balances.
- Healthcare RCM: Clean claim rates, denial velocity by payer (Aetna, UnitedHealthcare, Medicare), and average days in accounts receivable (DAR).

## Storage Engine: Why Apache Iceberg?

Historically, data lakes stored plain Parquet files on Amazon S3. However, plain Parquet files on object storage introduce severe production bugs:
- No ACID Transactions: If a worker pod crashes while writing a 50MB Parquet file, downstream readers encounter corrupt data.
- Expensive List Operations: Querying millions of partitioned files on S3 requires thousands of `LIST` API calls, adding seconds of latency to queries.
- Inflexible Schema Evolution: Adding a new tax category or a new insurance modifier requires rewriting historical files.

Apache Iceberg solves these issues by decoupling table metadata from object storage paths. Iceberg maintains a tree of hierarchical metadata files, manifest lists, and data files:

```
Iceberg Table Architecture:
Table Metadata (Version N)
       |
  Manifest List
   /          \
Manifest 1   Manifest 2
  /    \       /    \
Data1 Data2  Data3 Data4 (Parquet Files)
```

Iceberg provides three features essential for financial and clinical systems:
1. Snapshot Isolation: Readers always read from a consistent snapshot, even while thousands of extraction workers are writing concurrently.
2. Schema Evolution: You can rename columns, add optional fields, or reorder schemas with zero file rewrites.
3. Time Travel: You can execute queries against the exact state of the table at any historical timestamp: `SELECT * FROM claims FOR SYSTEM_TIME AS OF '2026-05-01 00:00:00'`.

### PyIceberg Implementation

Let us look at how an extraction worker writes Silver-tier invoices into an Iceberg table using `pyiceberg`:

```python
from pyiceberg.catalog import load_catalog
from pyiceberg.schema import Schema
from pyiceberg.types import (
    StringType, TimestampType, DecimalType, 
    NestedField, ListType, StructType
)
import pyarrow as pa
from decimal import Decimal
from datetime import datetime

# Connect to the enterprise REST or Glue catalog
catalog = load_catalog("enterprise_lakehouse", **{
    "type": "rest",
    "uri": "https://iceberg.internal.net",
    "s3.endpoint": "https://s3.us-east-1.amazonaws.com"
})

def append_to_silver_invoices(invoice_data: dict):
    table = catalog.load_table("silver_finance.canonical_invoices")
    
    # Map canonical data into an Arrow record batch
    arrow_table = pa.Table.from_pylist([
        {
            "invoice_number": invoice_data["invoice_number"],
            "supplier_tax_id": invoice_data["supplier_tax_identifier"],
            "issue_date": invoice_data["issue_date"],
            "payable_amount": Decimal(str(invoice_data["payable_amount"])),
            "currency": invoice_data["invoice_currency"],
            "ingested_at": datetime.utcnow()
        }
    ])
    
    # Atomic Iceberg append with snapshot commit
    table.append(arrow_table)
```

## Durable Workflow Orchestration with Temporal

Now let us examine the orchestration engine. 

A production document processing workflow is not a single function. It is a multi-step distributed pipeline:
1. Fetch document binary from S3.
2. Call Gemini 3.8 Flash for extraction.
3. Validate against Pydantic Common Data Model.
4. Check duplicate invoices in Redis.
5. Ingest into Apache Iceberg Silver layer.
6. Check business rules (e.g., matching invoice to purchase order).
7. If invoice exceeds $10,000, pause and await human manager approval.
8. Commit transaction to ERP (SAP / NetSuite).

If you orchestrate this with standard Celery tasks or basic cron loops, what happens if the worker pod restarts during Step 7? The task is lost, the ERP transaction is half-committed, and the invoice hangs in limbo.

Temporal solves this through Durable Execution. Temporal records every workflow event in an append-only event history. If a worker pod crashes, a network cable is cut, or a third-party API goes down, another worker picks up the workflow at the exact line of code where it left off, with all local variables preserved.

### Defining Temporal Activities

Activities perform the actual external network calls and computation. Each activity is given an explicit retry policy:

```python
from temporalio import activity
from datetime import timedelta
import asyncio

@activity.defn
async def extract_multimodal_document_activity(storage_uri: str) -> dict:
    # Invokes Gemini 3.8 Flash vision extraction
    # Automatically retried on transient errors
    raw_bytes = await fetch_from_storage(storage_uri)
    return await run_gemini_extraction(raw_bytes)

@activity.defn
async def validate_cdm_activity(raw_data: dict) -> dict:
    # Executes Pydantic validation
    # If this fails with a validation error, it is marked non-retryable
    canonical_model = InvoiceNormalizationService.map_to_peppol(raw_data)
    return canonical_model.model_dump()

@activity.defn
async def commit_to_iceberg_activity(canonical_data: dict):
    # Appends record to Silver Lakehouse
    append_to_silver_invoices(canonical_data)

@activity.defn
async def post_to_erp_activity(canonical_data: dict) -> str:
    # Communicates with external SAP / NetSuite API
    return await erp_client.create_bill(canonical_data)
```

### Defining the Durable Workflow

Now we connect our activities into a durable workflow. Notice how cleanly we can handle approval signals and long-running pauses:

```python
from temporalio import workflow
from temporalio.common import RetryPolicy
from datetime import timedelta

@workflow.defn
class InvoiceProcessingWorkflow:
    def __init__(self):
        self.approved_by_human = False
        self.rejection_reason = None

    @workflow.signal
    def human_approval_signal(self, approved: bool, reason: str = None):
        self.approved_by_human = approved
        self.rejection_reason = reason

    @workflow.run
    async def run(self, storage_uri: str, tenant_id: str) -> str:
        standard_retry = RetryPolicy(
            initial_interval=timedelta(seconds=2),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=60),
            maximum_attempts=5,
            non_retryable_error_types=["ValueError", "ValidationError"]
        )

        # 1. Extraction Activity
        raw_extraction = await workflow.execute_activity(
            extract_multimodal_document_activity,
            storage_uri,
            start_to_close_timeout=timedelta(minutes=3),
            retry_policy=standard_retry
        )

        # 2. Semantic Normalization & Invariant Validation
        canonical_invoice = await workflow.execute_activity(
            validate_cdm_activity,
            raw_extraction,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=standard_retry
        )

        # 3. Commit to Lakehouse Silver Layer
        await workflow.execute_activity(
            commit_to_iceberg_activity,
            canonical_invoice,
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=standard_retry
        )

        # 4. Human-in-the-Loop Threshold Check
        # Invoices over $10,000 require human sign-off
        payable_amount = float(canonical_invoice["payable_amount"])
        if payable_amount > 10000.00:
            # Workflow pauses here. Zero CPU used. State is saved durably.
            # Waits up to 72 hours for a human manager to approve via dashboard.
            await workflow.wait_condition(
                lambda: self.approved_by_human is True or self.rejection_reason is not None,
                timeout=timedelta(hours=72)
            )

            if not self.approved_by_human:
                return f"Invoice rejected by human manager: {self.rejection_reason}"

        # 5. Final ERP Mutation
        erp_transaction_id = await workflow.execute_activity(
            post_to_erp_activity,
            canonical_invoice,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=standard_retry
        )

        return f"Successfully processed invoice. ERP Transaction ID: {erp_transaction_id}"
```

## The Sagas Pattern: Handling Partial Failures

In distributed financial and healthcare systems, distributed transactions across heterogeneous systems (S3, Iceberg, SAP, Epic EHR) cannot rely on two-phase commit (2PC).

Instead, we implement the Sagas Pattern: For every forward action that alters external state, we define an idempotent compensating action.

If an invoice is successfully written to the Silver Lakehouse and posted to SAP, but a subsequent notification step fails catastrophically:
1. Forward Action: `post_to_erp(invoice)`
2. Compensating Action: `void_erp_bill(transaction_id)`

Temporal makes the Sagas pattern straightforward by allowing you to register compensating activities in standard `try/except` blocks:

```python
compensations = []
try:
    tx_id = await workflow.execute_activity(post_to_erp_activity, canonical_invoice)
    compensations.append(lambda: workflow.execute_activity(void_erp_bill_activity, tx_id))
    
    await workflow.execute_activity(notify_vendor_activity, canonical_invoice)
except Exception as e:
    # Execute compensations in reverse order
    for comp in reversed(compensations):
        await comp()
    raise e
```

## Summary and What Comes Next

In this third installment, we architected the enterprise storage and orchestration backbone:
- Implemented the Medallion Architecture, segregating raw Bronze blobs, validated Silver Common Data Models, and analytical Gold marts.
- Leveraged Apache Iceberg for transactional consistency, snapshot isolation, and regulatory time-travel queries.
- Deployed Temporal for durable execution, replacing fragile Celery scripts with fault-tolerant, pause-and-resume workflows.
- Implemented the Sagas pattern to guarantee zero orphaned records during distributed failures.

Now our documents are safely extracted, validated, and persisted. But how does an automated system evaluate whether an invoice line item matches an original vendor contract, or whether a healthcare claim meets an insurance company's medical necessity policy?

In Part 4 of this series, we will build the Hybrid Semantic Search and Knowledge Graph RAG layer: indexing complex enterprise contracts and payer coverage guidelines using pgvector, HNSW, BM25, and Reciprocal Rank Fusion.
