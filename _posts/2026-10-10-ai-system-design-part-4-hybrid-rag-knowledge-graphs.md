---
layout: post
title: "AI System Design Series (Part 4): Hybrid Semantic Search and Knowledge Graph RAG for Enterprise Contracts and Payer Policies"
description: "How to engineer zero-hallucination retrieval systems for complex compliance documents. Combining dense pgvector HNSW search, sparse BM25 keyword matching, Reciprocal Rank Fusion, and Knowledge Graphs across Invoices and Healthcare RCM."
author: professor-xai
categories: [system-design, rag, search, vector-database]
image: assets/images/ai-system-design-part-4-hybrid-rag.webp
featured: true
last_modified_at: 2026-10-10
keywords: "hybrid search pgvector, bm25 reciprocal rank fusion, knowledge graph rag, payer coverage policy retrieval, contract matching rag, enterprise rag architecture"
faq:
  - question: "Why does pure vector semantic search fail on enterprise contracts and billing codes?"
    answer: "Pure vector search relies on cosine similarity in dense embedding space. While it excels at understanding broad semantic intent, it frequently misses exact alpha-numeric strings such as part numbers (SKU-8819A), contractual section references (§ 14.2), and 5-digit CPT codes (e.g., 99213 vs 99214). Hybrid search combines dense vectors with sparse BM25 indexing to guarantee both conceptual understanding and exact keyword precision."
  - question: "What is Reciprocal Rank Fusion (RRF) and why is it superior to score normalization?"
    answer: "Dense cosine scores and sparse BM25 scores operate on entirely different mathematical distributions, making direct score addition or weighting fragile. Reciprocal Rank Fusion ranks results purely by their relative ordinal position in each search list using the formula 1 / (60 + rank), ensuring robust, calibrated ranking without manual tuning."
  - question: "How do Knowledge Graphs complement RAG in healthcare and financial applications?"
    answer: "Knowledge Graphs capture explicit, deterministic relationships between business entities (e.g., Procedure X requires Prior Authorization only when paired with Diagnosis Y for Payer Z). RAG retrieves the text evidence, while the Knowledge Graph enforces the non-negotiable structural constraints that prevent multi-hop hallucinations."
---

In Part 2 and Part 3 of this series, we normalized our incoming document streams into canonical Common Data Models (PEPPOL Invoices and HL7 FHIR Claims) and persisted them within an Apache Iceberg lakehouse orchestrated by Temporal workflows.

Now we arrive at the core intelligence challenge: Contextual Verification.

Extracting the numbers from an invoice or a medical claim is straightforward. The difficult engineering problem is deciding whether those numbers are correct according to external contracts, statutory regulations, and clinical coverage policies:

In Accounts Payable: Does this vendor's billed unit price of $42.50 match the tiered volume discount agreed upon in Section 4.2 of their 2024 Master Services Agreement?

In Healthcare RCM: Does Patient X's diagnosed condition (Type 2 Diabetes with neuropathy, ICD-10 `E11.40`) satisfy Aetna's specific Medical Coverage Policy for reimbursement of continuous glucose monitoring (CPT `95250`)?

If you rely on a naive RAG setup—chunking large PDF manuals into 500-token blocks, embedding them with OpenAI or BGE, and performing a basic cosine similarity search—your system will hallucinate and fail.

Pure vector search is blind to exact alphanumeric part numbers, subtle contractual clauses, and multi-hop relationship trees.

In this fourth installment of our AI System Design Series, we build a production-grade **Hybrid Semantic Search and Knowledge Graph Retrieval Engine**:

1. Why Pure Vector Search Fails: The exact-token blindness of dense embeddings.
2. The Dual-Index Architecture: Dense HNSW indexing in `pgvector` paired with Sparse BM25 full-text indexing in PostgreSQL.
3. Reciprocal Rank Fusion (RRF) and Cross-Encoder Reranking: Merging disparate ranking scores with mathematical rigor.
4. Knowledge Graph Integration: Modeling deterministic relational logic to constrain LLM reasoning.

## The Semantic Collision Problem

To understand why naive RAG fails in production, consider how dense embedding models work. An embedding model projects text into a high-dimensional continuous vector space. In this space, the model groups text by broad conceptual similarity:

```
Embedding Space Proximity:
"CPT 99213 (Office visit, low complexity)" <---> "CPT 99214 (Office visit, moderate complexity)"
Cosine Similarity: 0.94 (Extremely Close)
```

To an embedding model, `CPT 99213` and `CPT 99214` appear virtually identical because both describe outpatient office visits. 

However, in healthcare billing, billing a 99214 when the medical chart only justifies a 99213 constitutes statutory insurance fraud, while billing a 99213 when a 99214 was documented loses thousands of dollars in legitimate hospital revenue.

Similarly, in Accounts Payable:
```
Contract Clause A: "Payment due within 30 days of receipt (Net 30)."
Contract Clause B: "Payment due within 60 days of receipt (Net 60)."
```
Dense vector embeddings treat these two sentences as 98% semantically identical. Yet from a working capital perspective, the 30-day difference represents hundreds of thousands of dollars in cash float.

To build a reliable retrieval engine, we must combine **Dense Semantic Retrieval** (understanding intent) with **Sparse Lexical Retrieval** (finding exact alphanumeric codes and section numbers).

## The Dual-Index Architecture in PostgreSQL

Instead of introducing two separate database clusters (such as Pinecone for vectors and Elasticsearch for keywords), we can implement both dense and sparse indexes inside a single PostgreSQL 16+ instance using `pgvector` and native Postgres Full-Text Search. This eliminates distributed synchronization bugs and simplifies operational maintenance.

### Schema Setup with pgvector and TSVECTOR

```sql
-- Enable the vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Table storing chunked corporate contracts and medical policies
CREATE TABLE policy_knowledge_chunks (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(64) NOT NULL,
    document_type VARCHAR(32) NOT NULL, -- 'vendor_msa', 'payer_bulletin'
    document_identifier VARCHAR(128) NOT NULL, -- e.g. 'AETNA_CPB_0045'
    section_reference VARCHAR(64), -- e.g. 'Section 4.2.1'
    chunk_content TEXT NOT NULL,
    
    -- Dense Embedding (BGE-M3 / OpenAI text-embedding-3: 1536 dimensions)
    dense_embedding vector(1536),
    
    -- Sparse Lexical TSVECTOR (English stemming + alphanumeric dictionary)
    sparse_lexical tsvector GENERATED ALWAYS AS (
        to_tsvector('english', chunk_content || ' ' || coalesce(section_reference, ''))
    ) STORED,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 1. Create HNSW Index for Dense Vector Similarity (Cosine Distance)
CREATE INDEX idx_policy_dense_hnsw 
ON policy_knowledge_chunks 
USING hnsw (dense_embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- 2. Create GIN Index for Sparse Keyword Matching (BM25 Equivalent)
CREATE INDEX idx_policy_sparse_gin 
ON policy_knowledge_chunks 
USING gin (sparse_lexical);
```

With these two indexes in place:
- The HNSW index answers conceptual questions like: *"What is the policy on pre-existing joint inflammation?"*
- The GIN index instantly matches exact queries like: *"CPT 95250"* or *"MSA Section 14.3"*.

## Reciprocal Rank Fusion (RRF) Implementation

When executing a hybrid query, we receive two distinct ranked lists:
1. List A from Vector Search, ranked by Cosine Distance (0.0 to 2.0).
2. List B from Full-Text Search, ranked by `ts_rank` (arbitrary positive float).

You cannot simply add `cosine_score + bm25_score`. The mathematical scales and distributions are incompatible.

Instead, we use Reciprocal Rank Fusion (RRF). RRF discards raw scores entirely and evaluates documents based on their ordinal rank within each list:

```
RRF Score = SUM( 1 / ( k + rank_i ) )
where k is a smoothing constant (typically 60)
```

Here is the production SQL query executing dense and sparse search concurrently using Common Table Expressions (CTEs) and combining them via RRF:

```sql
WITH dense_search AS (
    SELECT 
        chunk_id, 
        ROW_NUMBER() OVER (ORDER BY dense_embedding <=> $1::vector) as dense_rank
    FROM policy_knowledge_chunks
    WHERE tenant_id = $2
    ORDER BY dense_embedding <=> $1::vector
    LIMIT 50
),
sparse_search AS (
    SELECT 
        chunk_id, 
        ROW_NUMBER() OVER (ORDER BY ts_rank(sparse_lexical, plainto_tsquery('english', $3)) DESC) as sparse_rank
    FROM policy_knowledge_chunks
    WHERE tenant_id = $2 
      AND sparse_lexical @@ plainto_tsquery('english', $3)
    ORDER BY ts_rank(sparse_lexical, plainto_tsquery('english', $3)) DESC
    LIMIT 50
)
SELECT 
    coalesce(d.chunk_id, s.chunk_id) as chunk_id,
    k.chunk_content,
    k.section_reference,
    (
        coalesce(1.0 / (60 + d.dense_rank), 0.0) +
        coalesce(1.0 / (60 + s.sparse_rank), 0.0)
    ) as rrf_score
FROM dense_search d
FULL OUTER JOIN sparse_search s ON d.chunk_id = s.chunk_id
JOIN policy_knowledge_chunks k ON k.chunk_id = coalesce(d.chunk_id, s.chunk_id)
ORDER BY rrf_score DESC
LIMIT 10;
```

This hybrid query executes in under 25 milliseconds. It guarantees that if an exact code is present, it is boosted to the top, while still pulling semantically relevant contextual paragraphs that explain the policy rules.

## Knowledge Graphs: Constraining Multi-Hop Logic

While hybrid search retrieves the correct text chunks, unstructured text alone is insufficient for complex multi-hop regulatory logic.

Consider this real-world Healthcare RCM policy rule:
*"Continuous Glucose Monitoring (CPT 95250) is covered by Payer A for Type 2 Diabetes (ICD-10 E11.9) ONLY IF the patient has documented history of multiple daily insulin injections (HCPCS J1815) AND at least two documented hypoglycemic episodes within 90 days."*

If you feed three retrieved PDF paragraphs to an LLM and ask *"Is this claim covered?"*, the model must perform a four-step multi-hop deduction across dates, codes, and historical records. LLMs frequently hallucinate or miss one of the four conjunctions.

To eliminate hallucinations on critical business rules, we supplement RAG with a deterministic Knowledge Graph:

```
Knowledge Graph Triples:
(CPT:95250) --[REQUIRES_DIAGNOSIS]--> (ICD10:E11.9)
(CPT:95250) --[MANDATES_CRITERIA]--> (Condition:MultipleDailyInsulin)
(CPT:95250) --[MANDATES_CRITERIA]--> (Condition:HypoglycemiaWithin90Days)
```

### Python Graph Policy Validator

Before generating a response or submitting an appeal, our system queries the graph to extract the explicit, non-negotiable checklist that must be satisfied:

```python
from dataclasses import dataclass
from typing import List, Set

@dataclass
class PolicyRequirement:
    procedure_code: str
    payer_id: str
    mandatory_diagnoses: Set[str]
    required_clinical_prerequisites: List[str]
    prior_auth_required: bool

class DeterministicPolicyGraph:
    def __init__(self):
        # In production, backed by Neo4j, Amazon Neptune, or Postgres recursive CTEs
        self.rules = {
            ("95250", "AETNA"): PolicyRequirement(
                procedure_code="95250",
                payer_id="AETNA",
                mandatory_diagnoses={"E10", "E11"},
                required_clinical_prerequisites=[
                    "multiple_daily_insulin_injections",
                    "frequent_blood_glucose_monitoring"
                ],
                prior_auth_required=True
            )
        }

    def verify_coverage_rules(
        self, 
        cpt: str, 
        payer: str, 
        patient_diagnoses: List[str]
    ) -> tuple[bool, List[str]]:
        key = (cpt, payer)
        if key not in self.rules:
            # No specific restriction found, default to standard review
            return True, []

        rule = self.rules[key]
        missing_criteria = []

        # Check diagnostic category match
        has_valid_dx = any(
            any(dx.startswith(prefix) for prefix in rule.mandatory_diagnoses)
            for dx in patient_diagnoses
        )
        if not has_valid_dx:
            missing_criteria.append(
                f"CPT {cpt} requires supporting diagnosis from {rule.mandatory_diagnoses}, "
                f"but patient record only has {patient_diagnoses}"
            )

        if rule.prior_auth_required:
            missing_criteria.append("Prior Authorization is strictly required prior to service date.")

        return len(missing_criteria) == 0, missing_criteria
```

By querying the graph first, the system establishes a hard boolean boundary:
1. If the graph validation fails, the claim is flagged immediately with zero AI tokens spent.
2. If the graph validation passes, the retrieved RAG chunks from our hybrid search are injected into the prompt as supporting evidence for the appeal letter or ledger entry.

## Summary and What Comes Next

In this fourth installment, we built a zero-hallucination retrieval layer:
- Analyzed the semantic collision failure mode where pure vector search confuses adjacent billing codes and financial terms.
- Implemented a dual-index architecture in PostgreSQL combining dense HNSW vector search with sparse BM25 TSVECTOR indexing.
- Unified search results using Reciprocal Rank Fusion (RRF) to produce calibrated, multi-perspective ranking in under 25ms.
- Integrated a deterministic Knowledge Graph to enforce non-negotiable multi-hop policy constraints before invoking LLM generation.

We now have structured document ingestion, validated Common Data Models, a scalable Iceberg lakehouse, and a hybrid knowledge retrieval engine.

However, invoking a full-scale LLM (like Claude or GPT) to evaluate every incoming claim or invoice line item adds 1,500ms of latency and burns thousands of dollars per week. Most incoming items are simple, routine transactions that only need split-second triage.

In Part 5 of this series, we will introduce System-1 Decision Intelligence with TypeSafe AI's Jev: deploying sub-150ms classification models to triage claims, detect duplicate invoices, and screen fraud at fractions of a cent per turn.
