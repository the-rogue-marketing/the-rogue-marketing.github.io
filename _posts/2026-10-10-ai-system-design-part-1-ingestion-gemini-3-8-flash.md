---
layout: post
title: "AI System Design Series (Part 1): Distributed Ingestion and Multimodal Extraction with Gemini 3.8 Flash, Kafka, and Redis Streams"
description: "Building production ingestion pipelines for complex enterprise documents. How to decouple ingestion with Kafka, manage backpressure with Redis Streams, and extract structured data using Gemini 3.8 Flash across Accounts Payable and Healthcare RCM."
author: professor-xai
categories: [system-design, ai-architecture, python, gemini-api]
image: assets/images/ai-system-design-part-1-ingestion.webp
featured: true
last_modified_at: 2026-10-10
keywords: "ai system design ingestion, gemini 3.8 flash multimodal, kafka ai document processing, redis streams worker queue, enterprise rcm ingestion, invoice ocr pipeline"
faq:
  - question: "Why decouple document ingestion from LLM extraction using Kafka or Redis Streams?"
    answer: "LLM extraction introduces variable latency ranging from 800 milliseconds to several seconds per document. If you process documents synchronously inside your HTTP request handler, spikes in traffic will saturate web server workers, cause gateway timeouts, and drop incoming webhooks. A message broker provides backpressure buffering and guaranteed delivery."
  - question: "How does Gemini 3.8 Flash handle multi-page scanned documents compared to legacy OCR?"
    answer: "Legacy optical character recognition pipelines require separating image preprocessing, text bounding box detection, layout analysis, and text extraction into multiple fragile stages. Gemini 3.8 Flash natively consumes image tokens directly, understanding spatial relationships, multi-column tables, and handwritten annotations in a single unified forward pass."
  - question: "How do you prevent duplicate document processing in high-throughput distributed pipelines?"
    answer: "Generate a deterministic SHA-256 hash of the normalized file binary at ingestion time. Store this hash in Redis with an atomic SETNX operation before enqueuing the document to Kafka. If another worker or client uploads the identical file within your deduplication window, the request is recognized immediately."
---

Most tutorials on building document AI systems present a trivial architecture. They show a basic FastAPI endpoint that receives a PDF, immediately calls an LLM API, parses the response, and writes it to a database. 

If you deploy that pattern to production in an enterprise processing hundreds of thousands of documents every month, your system will fail within the first week.

In real-world business environments, documents arrive in unpredictable bursts. Scanned PDFs are frequently blurred, rotated, or corrupt. Third-party LLM APIs occasionally return rate-limit errors or transient network timeouts. If your ingestion layer is tightly coupled to your extraction workers, your API gateway will exhaust its thread pool, drop webhooks, and corrupt database state.

This article is the first installment of our comprehensive AI System Design Series. Across this series, we will build a complete, production-grade enterprise automation platform that handles two demanding business domains:

1. Accounts Payable and Financial Invoicing: Ingesting high-volume supplier invoices, utility bills, crumpled mobile photo receipts, and delivery manifests across multiple currencies and tax jurisdictions.
2. Healthcare Revenue Cycle Management (RCM): Processing CMS-1500 professional claims, UB-04 institutional hospital bills, physician clinical notes, and multi-page prior-authorization fax transmissions.

In this first part, we focus entirely on the foundation: distributed data ingestion, stream buffering, backpressure control, and high-accuracy multimodal extraction using Gemini 3.8 Flash.

## Architectural Requirements and Failure Modes

Before writing any pipeline code, we must specify the non-negotiable operational requirements for an enterprise ingestion engine:

- Idempotency: Uploading the exact same document twice must never create duplicate ledger entries or duplicate medical claims.
- Backpressure Resilience: An influx of 50,000 invoices arriving at the end of the month must be safely buffered without crashing worker memory.
- Worker Decoupling: Document upload acknowledgment must complete in under 150 milliseconds, while actual AI extraction proceeds asynchronously in the background.
- Failure Isolation: A corrupt or unreadable 300-page document must be relegated to a dead-letter queue without blocking the queue for valid documents.
- Raw Data Preservation: The raw binary and extraction metadata must be stored immutably in a bronze data lake for auditability and compliance.

## Ingestion Architecture Blueprint

The ingestion engine consists of four decoupled layers:

The Gateway Layer receives document uploads through REST endpoints, SFTP drop zones, email scrapers, or direct EHR integration webhooks. It validates file types, calculates cryptographic checksums, and uploads the raw file to an object store (S3 or MinIO).

The Message Bus (Kafka) accepts lightweight event envelopes containing the file location, tenant metadata, and document type, routing them into partitioned topics (documents.invoices.raw and documents.healthcare.raw).

The Coordination Layer (Redis Streams) manages worker leasing, heartbeat tracking, distributed deduplication locks, and transient retry budgets.

The Worker Pool executes the heavy extraction logic using Gemini 3.8 Flash. Workers pull messages, retrieve the binary from object storage, downsample oversized pages, and invoke the model with strict Pydantic schemas.

## Step 1: Deterministic Checksum Deduplication

The very first action our gateway must take upon receiving a file is calculating its content hash. We use SHA-256 computed on the raw bytes:

```python
import hashlib
import redis.asyncio as redis
from fastapi import FastAPI, UploadFile, HTTPException, Depends

app = FastAPI(title="Enterprise Document Ingestion Gateway")
redis_client = redis.from_url("redis://localhost:6379/0")

async def verify_idempotency(file_bytes: bytes, tenant_id: str) -> str:
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    dedup_key = f"dedup:{tenant_id}:{file_hash}"
    
    # Atomic set with a 24-hour expiration window
    is_new = await redis_client.set(dedup_key, "processing", nx=True, ex=86400)
    if not is_new:
        status = await redis_client.get(dedup_key)
        raise HTTPException(
            status_code=409, 
            detail=f"Duplicate document detected. Current status: {status.decode('utf-8')}"
        )
    return file_hash
```

By enforcing this check at the network boundary, we immediately discard duplicate webhook deliveries and prevent duplicate database records before any cloud compute or AI tokens are consumed.

## Step 2: The Event Envelope and Queue Partitioning

Once verified, the raw file is persisted to object storage, and a lightweight event envelope is published to Kafka.

We intentionally avoid passing large file binaries through Kafka messages. Instead, we pass an immutable URI reference. Here is the canonical schema for our ingestion event envelope:

```python
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class DomainType(str, Enum):
    ACCOUNTS_PAYABLE = "accounts_payable"
    HEALTHCARE_RCM = "healthcare_rcm"

class IngestionEvent(BaseModel):
    event_id: str
    tenant_id: str
    domain: DomainType
    file_hash: str
    storage_uri: str
    content_type: str
    file_size_bytes: int
    received_at: datetime
    priority: int = Field(default=5, ge=1, le=10)
```

We partition our Kafka topics by tenant_id. This guarantees that all documents from a specific healthcare clinic or accounting subsidiary are processed in strict sequential order per tenant, while allowing our entire cluster of worker pods to scale horizontally across independent partitions.

## Step 3: Multimodal Extraction with Gemini 3.8 Flash

Why choose Gemini 3.8 Flash over legacy OCR engines or larger frontier models?

Legacy OCR engines like Tesseract, AWS Textract, or Google Cloud Document AI operate on rigid structural heuristics. When an invoice has an irregular multi-table layout, a handwritten subtotal, or a watermark across the page, traditional OCR engines drop lines, concatenate adjacent columns, and produce garbled text.

Gemini 3.8 Flash fundamentally changes this workflow. As a native multimodal model, it takes the high-resolution page rendering directly into its vision encoder. It understands spatial geometry, tabular grouping, and semantic intent simultaneously. 

Furthermore, Gemini 3.8 Flash is specifically tuned for long-horizon enterprise workflows and autonomous agents, delivering extraction speeds that are roughly four to six times faster than traditional heavy models at a fraction of the token cost.

### Schema Definition for Domain 1: Accounts Payable Invoices

Let us examine the structured Pydantic schema required for extracting an enterprise invoice:

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class InvoiceLineItem(BaseModel):
    item_index: int
    description: str
    quantity: float
    unit_price: float
    discount_amount: Optional[float] = 0.0
    tax_rate_percent: Optional[float] = 0.0
    line_total: float

class InvoiceExtractionSchema(BaseModel):
    invoice_number: str
    purchase_order_number: Optional[str] = None
    invoice_date: str = Field(description="ISO-8601 date format YYYY-MM-DD")
    due_date: Optional[str] = None
    vendor_name: str
    vendor_tax_id: Optional[str] = None
    vendor_iban_or_account: Optional[str] = None
    currency: str = Field(default="USD", max_length=3)
    line_items: List[InvoiceLineItem]
    subtotal_amount: float
    tax_amount: float
    total_amount: float
    confidence_flags: List[str] = Field(
        default_factory=list,
        description="Flags for unclear handwritten notes, calculation mismatches, or blurred text"
    )
```

### Schema Definition for Domain 2: Healthcare RCM Claims (CMS-1500)

Healthcare claims require a radically different level of ontological precision. The extraction model must capture National Provider Identifiers (NPI), diagnostic codes mapped to ICD-10-CM, procedure codes mapped to CPT/HCPCS, and billing modifiers:

```python
class ClaimServiceLine(BaseModel):
    line_number: int
    date_of_service: str
    place_of_service_code: str
    cpt_hcpcs_code: str = Field(description="5-character procedure code")
    modifier_codes: List[str] = Field(default_factory=list, description="e.g. 25, 59, RT, LT")
    diagnosis_pointers: List[str] = Field(description="References to diagnosis codes, e.g. A, B")
    charge_amount: float
    unit_count: int

class HealthcareClaimSchema(BaseModel):
    claim_type: str = Field(default="CMS-1500", description="CMS-1500 or UB-04")
    patient_account_number: str
    patient_date_of_birth: str
    insured_id_number: str
    payer_name: str
    billing_provider_name: str
    billing_provider_npi: str = Field(min_length=10, max_length=10)
    rendering_provider_npi: Optional[str] = None
    primary_diagnosis_code: str = Field(description="ICD-10-CM diagnosis code without decimal")
    secondary_diagnosis_codes: List[str] = Field(default_factory=list)
    service_lines: List[ClaimServiceLine]
    total_charge: float
    prior_authorization_number: Optional[str] = None
```

## Step 4: Building the Async Worker Pipeline

Now we assemble the production extraction worker. The worker reads from Kafka, fetches the image binary from S3, downsamples the image if it exceeds hardware resolution limits, and executes the extraction turn using the official Google GenAI SDK.

```python
import io
from PIL import Image
from google import genai
from google.genai import types

class DocumentExtractionWorker:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-3.8-flash"

    def normalize_image(self, raw_bytes: bytes) -> bytes:
        """
        Resize oversized images to preserve visual tokens while keeping
        image dimensions within optimal vision encoder bounds.
        """
        img = Image.open(io.BytesIO(raw_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        max_dimension = 2048
        width, height = img.size
        if width > max_dimension or height > max_dimension:
            scaling_factor = max_dimension / max(width, height)
            new_size = (int(width * scaling_factor), int(height * scaling_factor))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            
        output_buffer = io.BytesIO()
        img.save(output_buffer, format="JPEG", quality=85)
        return output_buffer.getvalue()

    async def extract_invoice(self, image_bytes: bytes) -> InvoiceExtractionSchema:
        clean_bytes = self.normalize_image(image_bytes)
        
        prompt = (
            "You are a precision accounts payable data extraction engine. "
            "Extract all financial entities, vendor details, and line items from this invoice. "
            "Validate that the sum of line_total items matches subtotal_amount. "
            "If text is ambiguous or handwritten, document it inside confidence_flags."
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[
                types.Part.from_bytes(data=clean_bytes, mime_type="image/jpeg"),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=InvoiceExtractionSchema,
                temperature=0.0
            )
        )
        
        # Pydantic validates the returned structured JSON output
        return InvoiceExtractionSchema.model_validate_json(response.text)
```

## Production Hardening: Rate Limits and Dead-Letter Queues

When processing tens of thousands of documents concurrently, you will inevitably encounter temporary API throttles or malformed inputs. Never allow an unhandled exception to drop a message or crash a worker pod.

Implement a dual-state retry pattern:

1. Transient Errors (HTTP 429 Too Many Requests, HTTP 503 Service Unavailable): Apply exponential backoff with jitter. Requeue the event to Redis Streams with an incremented retry counter. If retries exceed five attempts, route to a secondary backup provider or alert the on-call engineer.
2. Permanent Schema Failures (corrupted binary, unreadable blank page, structural schema mismatch): Immediately write the failed payload, error traceback, and raw file path to a dedicated Dead-Letter Queue (DLQ). Notify the exception triage dashboard for human review without halting the worker loop.

```python
async def process_with_resilience(worker: DocumentExtractionWorker, event: IngestionEvent):
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            raw_bytes = await fetch_from_storage(event.storage_uri)
            extracted_data = await worker.extract_invoice(raw_bytes)
            await persist_to_bronze_lake(event, extracted_data)
            await redis_client.set(f"status:{event.file_hash}", "extracted", ex=86400)
            return
        except genai.errors.APIError as e:
            if attempt == max_retries:
                await push_to_dead_letter_queue(event, str(e))
            else:
                backoff_seconds = (2 ** attempt) + 0.5
                await asyncio.sleep(backoff_seconds)
        except Exception as e:
            # Fatal error (e.g. invalid document schema)
            await push_to_dead_letter_queue(event, str(e))
            break
```

## Summary and What Comes Next

In this first part, we established the ingestion backbone of our autonomous document platform:
- Decoupled ingestion endpoints from heavy extraction using Kafka and Redis Streams.
- Prevented duplicate processing at the network boundary using SHA-256 idempotency locks.
- Established strict, type-safe extraction schemas for Accounts Payable and Healthcare RCM.
- Leveraged Gemini 3.8 Flash for sub-second multimodal vision extraction without brittle traditional OCR stages.

Raw JSON extraction alone is not enough to run a company. In production, raw invoice data must conform to global accounting standards like PEPPOL and Universal Business Language (UBL), while healthcare claim data must adhere to strict HL7 FHIR structures, ICD-10 diagnostic trees, and HIPAA X12 EDI formats.

In Part 2 of this series, we will dive deep into Domain Ontologies and Common Data Models (CDM): building canonical semantic layers that transform raw LLM extractions into enterprise-compliant financial and clinical state machines.
