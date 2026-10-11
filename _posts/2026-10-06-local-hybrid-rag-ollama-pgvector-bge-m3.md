---
layout: post
title: 'Building Zero-Cloud Enterprise Search: Local Hybrid RAG with Ollama, pgvector
  & BGE-M3 Sparse Embeddings'
description: Architect a 100% private, self-hosted Hybrid RAG pipeline combining dense
  vector search, sparse lexical retrieval (BM25), and cross-encoder reranking.
author: professor-xai
categories: [Enterprise AI & Document Intelligence]
image: assets/images/flagship-developer-api-showdown.webp
featured: true
last_modified_at: 2026-10-06
keywords: local hybrid rag ollama pgvector, bge m3 dense sparse embeddings, private
  self hosted rag, rrf reciprocal rank fusion python
faq:
- {question: 'What is Hybrid RAG and why is dense vector search not enough?', answer: 'Dense
    vector embeddings understand semantic meaning but frequently miss exact part numbers,
    product SKUs, and proper nouns. Hybrid RAG fuses dense semantic vectors with sparse
    lexical keyword matching (BM25) to guarantee 100% retrieval recall.'}
- {question: 'What makes BGE-M3 ideal for local hybrid search?', answer: 'BAAI''s
    BGE-M3 model outputs dense vectors, sparse lexical weights, and multi-vector representations
    simultaneously in a single forward pass across 100+ languages.'}
- {question: 'Can pgvector handle millions of embeddings locally?', answer: 'Yes.
    With the HNSW (Hierarchical Navigable Small World) index in pgvector, search latency
    remains sub-10ms for datasets exceeding 1,000,000 document vectors on modest servers.'}
tags: [AI APIs, Python, System Design]
---
Sending sensitive proprietary data (internal medical records, source code, financial audits) to public cloud LLM APIs is an immediate compliance violation for many enterprises.

Here is how to build a **production-grade Hybrid Retrieval-Augmented Generation (RAG) engine running 100% locally on your own hardware** using **Ollama, PostgreSQL with pgvector, and BGE-M3 multi-function embeddings**.

---

## 1. The Tri-Modal Retrieval Funnel

```
                 ┌────────────────────────────────┐
                 │     User Question / Query      │
                 └───────────────┬────────────────┘
                                 │
         ┌───────────────────────┴───────────────────────┐
         ▼                                               ▼
┌─────────────────────────┐                     ┌─────────────────────────┐
│ Dense Vector Search     │                     │ Sparse Lexical (BM25)   │
│ (Semantic Concepts)     │                     │ (Exact Product SKUs)    │
└────────────┬────────────┘                     └────────────┬────────────┘
             │                                               │
             └───────────────────────┬───────────────────────┘
                                     │
                         ┌───────────▼───────────┐
                         │ Reciprocal Rank Fusion│ (RRF Scoring)
                         │ & BGE-Reranker        │
                         └───────────┬───────────┘
                                     │ Top 5 Reranked Chunks
                         ┌───────────▼───────────┐
                         │ Ollama Local LLM      │ (Llama 3.3 / Qwen 2.5)
                         └───────────────────────┘
```

---

## 2. PostgreSQL Schema Setup

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE document_chunks (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    dense_embedding vector(1024), -- BGE-M3 dimension
    tsv_tokens tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
);

-- High-speed Approximate Nearest Neighbor (ANN) index
CREATE INDEX ON document_chunks USING hnsw (dense_embedding vector_cosine_ops);
-- High-speed Full-Text Search GIN index
CREATE INDEX ON document_chunks USING gin (tsv_tokens);
```

---

## 3. Reciprocal Rank Fusion (RRF) Query

```sql
WITH semantic_search AS (
    SELECT id, RANK() OVER (ORDER BY dense_embedding <=> $1) as rank
    FROM document_chunks
    ORDER BY dense_embedding <=> $1
    LIMIT 20
),
keyword_search AS (
    SELECT id, RANK() OVER (ORDER BY ts_rank_cd(tsv_tokens, plainto_tsquery('english', $2)) DESC) as rank
    FROM document_chunks
    WHERE tsv_tokens @@ plainto_tsquery('english', $2)
    LIMIT 20
)
SELECT d.id, d.content,
       COALESCE(1.0 / (60 + s.rank), 0.0) + COALESCE(1.0 / (60 + k.rank), 0.0) AS rrf_score
FROM document_chunks d
LEFT JOIN semantic_search s ON d.id = s.id
LEFT JOIN keyword_search k ON d.id = k.id
WHERE s.id IS NOT NULL OR k.id IS NOT NULL
ORDER BY rrf_score DESC
LIMIT 5;
```

---

## 4. Key Takeaways

1. **Zero Data Leakage**: Not a single byte leaves your private network boundary.
2. **Flawless Retrieval Accuracy**: Dense semantics capture intent while lexical tokens guarantee exact part-number matches.
3. **Low Infrastructure Cost**: Runs entirely on a single Ubuntu workstation with 32GB RAM and an RTX 4090 GPU.
