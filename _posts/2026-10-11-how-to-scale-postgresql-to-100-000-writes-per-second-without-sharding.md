---
layout: post
title: How to Scale PostgreSQL to 100,000 Writes Per Second Without Sharding
description: An exhaustive systems engineering guide to maxing out single-node PostgreSQL
  write throughput. Learn unlogged tables, copy-in batching, write-ahead log (WAL)
  tuning, NVMe striping, and kernel fsync pipelining.
date: 2026-10-11 12:00:00 +0000
image: assets/images/postgres-scaling-2026.webp
categories: [System Design & Scalability]
keywords: scale postgresql 100k writes per second, postgres write throughput tuning,
  wal group commit optimization, postgresql without sharding, nvme kernel fsync pipeline
faqs:
- {question: 'Can a single PostgreSQL instance handle 100,000 writes per second?',
  answer: 'Yes, when architected properly with bulk ingest patterns, deferred constraints,
    connection pooling, and tuned Write-Ahead Logging (WAL) on enterprise NVMe PCIe
    5.0 storage.'}
- {question: 'Why is sharding often the wrong first choice for write-heavy workloads?',
  answer: 'Sharding introduces distributed transactions (2PC), network hops, re-balancing
    overhead, cross-shard joins, and massive operational complexity. 95% of applications
    jump to Citus or CockroachDB before exhausting single-node hardware capabilities.'}
- {question: 'What is the single biggest bottleneck in high-throughput PostgreSQL
    writes?', answer: The Write-Ahead Log (WAL) fsync synchronization. Calling synchronous
    fsync on individual row INSERTs locks the CPU on storage I/O barriers. Group commit
    and synchronous_commit configuration shifts this from I/O bound to CPU bound.}
tags: [PostgreSQL, System Design]
---
Before you split your database into a distributed cluster—introducing two-phase commit overhead, distributed deadlocks, and cross-node network latency—you should know this:

**A single optimized PostgreSQL instance on modern hardware can sustain over 100,000 ACID writes per second.**

Most engineering teams leap prematurely into horizontal sharding (Citus, Vitess, Spanner) when their bottleneck is not PostgreSQL's relational engine, but **naive connection concurrency, single-row INSERT patterns, and uncalibrated Write-Ahead Log (WAL) disk flush barriers**.

Here is the exact production engineering playbook to push PostgreSQL to 100,000+ writes per second on a single machine.

---

## 1. The Physics of 100k Writes/sec: The Latency Budget

To achieve 100,000 writes per second:

$$\text{Throughput} = \frac{\text{Batch Size}}{\text{Round-Trip Network Latency} + \text{Disk WAL Flush Time}}$$

If every write is an isolated `INSERT INTO events VALUES (...)` with synchronous round-trip acknowledgment:
- Even at **1ms** local network ping, single-threaded throughput caps at **1,000 writes/sec**.
- With 100 concurrent connections, you hit a hard wall at **10,000 to 15,000 writes/sec** due to WAL lock contention.

To reach 100,000 writes/sec, we must transition from single-statement row-by-row transactions to **micro-batched ingest pipelines**.

---

## 2. Kernel & Storage Architecture: Eliminating the WAL Wall

The primary bottleneck for relational database writes is the storage barrier: `fsync()`.

| Configuration Setting | Default Value | 100k Writes/sec Target | Technical Rationale |
| :--- | :--- | :--- | :--- |
| `synchronous_commit` | `on` | `off` or `local` | Acknowledges transaction once committed in memory buffer; flushes asynchronously every `wal_writer_delay` (prevents per-transaction I/O stall). |
| `wal_writer_delay` | `200ms` | `10ms` | Tightens the asynchronous flush window, limiting maximum potential data loss window to 10ms of transactions upon sudden power severance. |
| `commit_delay` | `0` | `20` to `50` (microseconds) | Enforces group commit: batches concurrent transactions into a single physical NVMe flush. |
| `commit_siblings` | `5` | `10` | Minimum concurrent transactions required before `commit_delay` engages. |
| `max_wal_size` | `1GB` | `64GB` - `128GB` | Eliminates frequent background checkpoint spikes that stall incoming writes. |
| `checkpoint_completion_target` | `0.9` | `0.95` | Smooths out disk I/O over the full checkpoint window. |

---

## 3. High-Throughput Ingestion Patterns

### A. The Binary `COPY` Protocol (250,000+ rows/sec)
Never use ORM `save()` loops or plain `INSERT` statements for high-throughput ingestion. Utilize the PostgreSQL binary streaming `COPY FROM STDIN (FORMAT binary)` protocol via pgx (Go) or asyncpg (Python).

### B. Micro-Batching with `UNNEST()`
If application semantics require parameterized SQL:

```sql
INSERT INTO sensor_telemetry (device_id, payload, recorded_at)
SELECT * FROM UNNEST(
    $1::uuid[],
    $2::jsonb[],
    $3::timestamptz[]
);
```
Passing arrays of 500 to 2,000 elements transforms 1,000 round-trips into a single parse-bind-execute cycle.

---

## 4. Indexing Discipline: The Write Amplification Tax

Every index on a table multiplies the write amplification factor:
- **1 Table with 5 Indexes** = 1 heap write + 5 separate B-tree balance updates.
- Under 100,000 writes/sec, 5 indexes generate **600,000 storage modifications per second**.

### Production Rules:
1. **Drop Unused Indexes**: Keep only primary key and critical point-lookup query paths.
2. **Use BRIN Instead of B-Tree for Append-Only Time-Series**: Block Range Indexes (BRIN) take **99% less memory and write overhead** than standard B-Trees by indexing page min/max values rather than every row.
3. **Partition by Range (Daily/Weekly)**: Eliminates B-tree re-balancing lock contention on massive multi-gigabyte index trees.

---

## 5. Summary Checklist Before You Shard

1. **Verify NVMe Direct-I/O Bandwidth**: Ensure your storage delivers >400,000 random write IOPS.
2. **Deploy PgBouncer in Transaction Pooling Mode**: Cap active PostgreSQL worker processes to 2x CPU core count to eliminate context switching.
3. **Adopt Binary COPY or Micro-Batching**: Never send single-row INSERT statements over the wire.
4. **Tune WAL Group Commit**: Let concurrent writes share physical disk flush cycles.
