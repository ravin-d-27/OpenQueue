# OpenQueue — Concept & Technical Documentation

OpenQueue is a hosted, PostgreSQL-backed job queue service designed to replace Redis-backed queues for many workloads. It provides a clean HTTP API for **producers** (clients that enqueue work) and **workers** (processes that execute work). OpenQueue is built around a simple idea:

> A queue is a table of jobs. Workers safely “lease” jobs using database row locking, then **ack** (success) or **nack** (failure) with a lease token.

This document explains the *why*, the *how*, and the technical details so a new contributor or user can understand the project end-to-end.

---

## Production readiness

OpenQueue can run in production, but “production-ready” depends on how you deploy it (single instance vs multi-replica) and what guarantees you expect. This section describes:

1) what is already implemented in this repository, and  
2) what you still need to do to confidently operate OpenQueue as a hosted queue service.

### Implemented production-grade features

#### 1) Core queue correctness & reliability
- **Leasing with row locking**: Workers lease jobs using Postgres locking (`FOR UPDATE SKIP LOCKED`) to safely handle concurrency.
- **Visibility timeout recovery**: Jobs stuck in `processing` become leaseable again when `locked_until < NOW()` (prevents permanent “stuck” jobs after worker crashes).
- **Lease renewal (heartbeat)**: Workers can extend `locked_until` for long-running jobs using a heartbeat endpoint.
- **ACK / NACK with lease tokens**: Workers must provide `lease_token` to ack/nack/heartbeat, preventing stale workers from updating job state.
- **Retry backoff with scheduling**: Retries are scheduled by setting `run_at` into the future (exponential backoff with a cap).
- **Dead-letter queue (DLQ)**: Jobs that exhaust retries (or have retry disabled) transition to `status='dead'` with `dead_at`/`dead_reason`.

#### 2) Database integrity: constraints and indexes
- **DB-level status constraint**: `CHECK (status IN (...))` prevents invalid states.
- **Retry bounds constraints**: non-negative retry counts and max retries.
- **Indexes for hot paths**:
  - lease hot path: `(user_id, queue_name, run_at, priority DESC, created_at) WHERE status='pending'`
  - recovery path: `(user_id, queue_name, locked_until) WHERE status='processing'`
  - DLQ listing: `(user_id, queue_name, dead_at) WHERE status='dead'`

#### 3) Migrations
- **Alembic migrations included**: an initial migration exists to create users/jobs with constraints and indexes.
- **Docker Compose applies migrations at startup**: `alembic upgrade head` is run before starting the API.

#### 4) Observability (baseline)
- **Request IDs**: every request gets `X-Request-ID`.
- **Structured request logging**: logs include method/path/status/duration and request id.
- **Prometheus metrics**: `/metrics` exposes counters/histograms for HTTP and key queue operations.

#### 5) Rate limiting (baseline)
- **In-memory token bucket** rate limits exist for:
  - enqueue, lease, ack, nack, heartbeat
  - job listing and queue stats
- This is **per process** (per replica). It protects a single-node deployment and limits blast radius in development.

#### 6) Readiness checks
- `/health`: liveness probe (process is up).
- `/ready`: readiness probe (currently uses a DB-backed dependency path to confirm DB connectivity).

#### 7) Background maintenance (library included)
- A maintenance module exists to:
  - reap expired leases (optional policy hook)
  - delete old jobs (retention)
  - run a periodic maintenance loop
- Recommended usage is a **separate maintenance process/container**, not the API process.

---

### What you still need to add to be “production ready” (recommended)

These are the typical gaps that cause outages or security incidents in hosted systems.

#### A) Distributed rate limiting and quotas (multi-replica requirement)
Current rate limiting is per-instance. For a hosted system with multiple API replicas you should implement one of:
- **Gateway-level rate limiting** (recommended): Nginx/Envoy/Cloudflare/API Gateway based, keyed by API token/user id.
- **Shared-store limiter** (Redis/Postgres): consistent limits across replicas.

Add quotas beyond RPS:
- max payload size per job and result
- max queue depth per tenant (hard cap)
- max concurrent in-flight `processing` jobs per tenant/queue

#### B) API key management + rotation (recommended for hosted)
Today you can store one token hash per user. For a hosted product you typically need:
- multiple API keys per user (table like `api_keys`)
- last_used_at per key
- revoke/rotate keys without downtime
- optional scoped keys (read-only dashboard vs worker keys)

#### C) Audit/attempt trail (strongly recommended)
Add a `job_attempts` table that records each lease/ack/nack event:
- attempt id (UUID)
- job_id, user_id
- worker_id
- leased_at, acked_at, nacked_at
- lease_token (or attempt_token)
- error/result snapshot
- duration
This enables:
- debugging (“why did this fail?”)
- user-facing history in dashboards
- accurate metrics

#### D) Testing & CI (must-have for correctness)
You should enforce correctness with:
- integration tests against Postgres:
  - concurrent leasing never duplicates jobs
  - lease-expiry recovery works
  - heartbeat extends leases correctly
  - backoff delays leasing until run_at
  - DLQ transition after retries exhausted
- a CI pipeline that runs:
  - migrations
  - tests
  - basic lint/type checks (optional but recommended)

#### E) Readiness without auth + DB ping
Today readiness depends on a DB-backed dependency path. For production, add an explicit DB ping:
- `SELECT 1` using the pool
- optional: confirm migration version and critical tables exist

#### F) Operational hardening
- configurable DB pool sizing
- statement timeouts
- request timeouts (reverse proxy)
- retention policy defaults and tooling
- avoid high-cardinality metrics labels (do not label by job_id, token, user email)
- API versioning (`/v1`) to stabilize client contracts

---

### Practical “Production-ready” definition for OpenQueue

OpenQueue is “production-ready” when you can:
1) survive worker crashes without losing jobs (visibility timeout recovery)  
2) safely run long jobs (heartbeat)  
3) avoid retry storms (backoff via run_at)  
4) isolate and inspect permanent failures (DLQ)  
5) evolve schema safely (migrations)  
6) observe and troubleshoot (logs + metrics)  
7) protect the platform from abuse (quotas + distributed rate limiting)  
8) prove correctness continuously (integration tests + CI)

---

## Table of Contents

1. [What OpenQueue is](#what-openqueue-is)
2. [Who it is for](#who-it-is-for)
3. [How it compares conceptually](#how-it-compares-conceptually)
4. [Core concepts](#core-concepts)
   - [Producers and Workers](#producers-and-workers)
   - [Jobs](#jobs)
   - [Leases and Lease Tokens](#leases-and-lease-tokens)
   - [Visibility Timeout (Lease Expiry Recovery)](#visibility-timeout-lease-expiry-recovery)
   - [Lease renewal (Heartbeat) for long-running jobs](#lease-renewal-heartbeat-for-long-running-jobs)
   - [ACK / NACK](#ack--nack)
   - [Retries](#retries)
   - [Retry backoff and scheduling with `run_at`](#retry-backoff-and-scheduling-with-run_at)
   - [Dead-letter queue (DLQ)](#dead-letter-queue-dlq)
   - [At-least-once delivery and idempotency](#at-least-once-delivery-and-idempotency)
5. [System architecture](#system-architecture)
6. [Database model](#database-model)
7. [Queue algorithm (SQL-level)](#queue-algorithm-sql-level)
8. [API surface (high level)](#api-surface-high-level)
9. [Operational considerations](#operational-considerations)
10. [Production readiness checklist](#production-readiness-checklist)
11. [Glossary](#glossary)

---

## What OpenQueue is

OpenQueue is a multi-tenant queue service that:
- stores jobs in PostgreSQL (JSONB payloads/results)
- exposes HTTP endpoints to enqueue and process jobs
- supports concurrent workers safely
- tracks job status and basic retry logic

OpenQueue is intentionally designed around **Postgres** rather than an in-memory broker. This can simplify infrastructure for many teams:
- fewer moving pieces (often you already operate Postgres)
- jobs can be persisted and inspected using standard SQL tools
- strong consistency and robust locking primitives

---

## Who it is for

OpenQueue is a good fit when:
- you want a hosted queue with an HTTP API
- you want persistence and inspectability in a relational database
- you can tolerate **at-least-once** job execution semantics
- you want a simpler operational story than running Redis + queue tooling

OpenQueue is *not* a good fit when:
- you require ultra-low-latency queue operations at very high throughput (Redis/Kafka-style)
- you require exactly-once delivery semantics without idempotent handlers
- you need long-term event streaming (Kafka-style) rather than task queues

---

## How it compares conceptually

OpenQueue resembles Redis queues and classic job queue systems but uses Postgres:

- Redis `BRPOP` / `RPOPLPUSH` behavior is approximated by:
  - **lease**: atomically claim a job (`SELECT ... FOR UPDATE SKIP LOCKED`)
  - **ack/nack**: update job state with a lease token check

- Redis “visibility timeout” patterns are implemented via:
  - `locked_until`: a lease expiry timestamp
  - re-leasing “stuck” jobs once the lease expires

### How OpenQueue is different (and when it is better) than “Redis caching”
Redis is often described as a “cache,” but Redis is also used as a **message broker / queue backend**. OpenQueue is not a cache; it is a **durable queue service** backed by PostgreSQL.

#### 1) Persistence and inspectability (OpenQueue advantage)
With Redis queues, durability depends on configuration (AOF/RDB) and operational practices. With OpenQueue:
- jobs are **rows in Postgres**
- you can inspect, debug, and audit jobs using standard SQL tools
- you can join job data with other relational data if you choose

This is especially helpful for:
- compliance/audit needs
- debugging “why is this stuck?”
- building dashboards and analytics

#### 2) Operational simplicity (OpenQueue advantage in many stacks)
Many teams already run Postgres. Adding OpenQueue may avoid introducing:
- a new stateful service (Redis) to operate
- queue-specific Redis patterns and tooling

For some deployments, “Postgres only” is simpler than “Postgres + Redis”.

#### 3) Multi-tenant hosting model (OpenQueue advantage for a hosted service)
OpenQueue is designed from the start to be multi-tenant:
- every job is scoped to a `user_id`
- API tokens map to users
- job listing and stats are naturally per-tenant

This fits the “hosted queue service” model directly.

#### 4) Reliability semantics: leases + visibility timeout (OpenQueue advantage)
OpenQueue uses:
- row locking (`FOR UPDATE SKIP LOCKED`) to safely lease jobs
- lease tokens to prevent stale updates
- visibility-timeout recovery so jobs aren’t lost when workers crash

Redis queues can achieve similar behavior, but it often requires careful patterns (e.g. processing lists, heartbeats, requeueing logic) implemented at the application level.

#### 5) Performance and latency (Redis advantage)
Redis is in-memory and extremely fast for queue primitives.
In general, Redis will win on:
- ultra-low latency
- very high throughput (jobs/sec)
- workloads that need sub-millisecond queue operations

OpenQueue relies on Postgres transactions and indexes, so it will be slower than Redis for the same hardware, especially at very high QPS.

#### 6) Scaling model (tradeoff)
- Redis typically scales by running Redis (or Redis Cluster) and scaling workers.
- OpenQueue scales by tuning Postgres (indexes, connection pools, instance sizing) and scaling workers. At very large scales you may need:
  - partitioning strategies
  - dedicated DB resources for the queue tables
  - careful query/index tuning

#### 7) When OpenQueue is the better choice
OpenQueue is often a better choice when you want:
- durable queues with strong inspectability
- a hosted multi-tenant queue API
- fewer infrastructure components
- SQL-based debugging and operational tooling

#### 8) When Redis is the better choice
Redis is often a better choice when you need:
- extremely high throughput and very low latency
- heavy burst traffic with minimal DB overhead
- existing Redis infrastructure and operational maturity

**Bottom line:** OpenQueue is “better” than Redis *as a queue backend* when durability, inspectability, and a Postgres-centric operational model matter more than peak performance. Redis is “better” when raw speed and throughput are the primary goals.

---

## Core concepts

### Producers and Workers

**Producer**: an application that creates jobs (work items) by sending HTTP requests to OpenQueue. Producers do not execute jobs.

**Worker (BYOW)**: “Bring Your Own Worker.” Users run their own worker process that:
1. calls `lease` to get a job
2. executes the workload
3. calls `ack` (success) or `nack` (failure)

This separation allows scaling producers and workers independently.

---

### Jobs

A job is a record with:
- an id (UUID)
- a queue name (string)
- a payload (JSON object)
- a status (pending/processing/completed/failed/etc.)
- metadata (priority, retries, timestamps)

Jobs live in the database and are the source of truth.

---

### Leases and Lease Tokens

A lease is a temporary claim on a job by a worker. It is represented by:
- `locked_by`: worker identifier (string)
- `locked_until`: lease expiry time (timestamp)
- `lease_token`: opaque token (UUID) required for ack/nack

**Why leases matter:** if two workers tried to process the same job concurrently, you could get double execution. Leasing + row locking prevents that.

---

### Visibility Timeout (Lease Expiry Recovery)

In real systems, workers crash. Without recovery, a leased job could remain stuck forever in `processing`. OpenQueue solves this with a visibility timeout:

- If a job is in `processing` and its lease expires (`locked_until < NOW()`), it becomes eligible to be leased again.
- When the job is re-leased, it receives a **new** lease token, so the original worker can no longer ack/nack.

This yields at-least-once processing semantics.

### Lease renewal (Heartbeat) for long-running jobs

Visibility timeout recovery prevents jobs from being stuck forever, but it introduces a new challenge: **long-running jobs**.

If a job legitimately takes longer than its lease duration and the worker does nothing, the lease can expire and the job can be re-leased to another worker. That can lead to duplicate processing.

OpenQueue supports **lease renewal** via a heartbeat mechanism:

- Workers periodically call a heartbeat endpoint while they are processing a job.
- The server extends `locked_until` forward from the current time, keeping the job leased to that worker.
- Heartbeat requires the current `lease_token`, so only the worker holding the lease can extend it.

Conceptually:

1. Worker leases a job, receiving `lease_token` and `lease_expires_at`.
2. Worker processes the job.
3. If processing is still ongoing, the worker calls heartbeat before expiry.
4. OpenQueue updates `locked_until = NOW() + lease_seconds`.

This keeps the system safe for long-running workloads while still allowing recovery for crashed workers.

---

### ACK / NACK

**ACK**: worker reports successful completion.
- updates job status to `completed`
- stores optional `result`
- clears lease metadata (`locked_*`, `lease_token`)

**NACK**: worker reports failure.
- stores `error_text`
- either:
  - requeues the job back to `pending` if retries remain and retry is allowed, or
  - marks it `failed`

Both ACK and NACK require the correct `lease_token` to prevent stale workers from incorrectly updating job state.

---

### Retries

Retries are controlled by:
- `retry_count`
- `max_retries`

OpenQueue’s retry mechanism is triggered by `nack`:

- If `retry=true` and retries remain, the job is requeued to `pending` and `retry_count` increments.
- If retries are exhausted (or retry is disabled), the job is moved to the dead-letter queue (DLQ) with status `dead`.

### Retry backoff and scheduling with `run_at`

Naively retrying immediately can cause “retry storms” (rapid repeated failures that waste worker/DB resources). OpenQueue uses `run_at` to schedule retries with backoff:

- `run_at` means “do not lease this job before this timestamp.”
- When a job is retried, OpenQueue sets `run_at = NOW() + backoff_interval`.
- The lease query only considers pending jobs where `run_at <= NOW()`.

Backoff is typically exponential (1s, 2s, 4s, 8s, …) with a cap. This improves stability under failure conditions and gives dependent systems time to recover.

This same `run_at` field can also be used for delayed jobs (enqueue now, run later), depending on the producer API design.

### Dead-letter queue (DLQ)

A dead-letter queue is where jobs go when they cannot be successfully processed after retries.

In OpenQueue:
- DLQ jobs have `status = 'dead'`
- `dead_at` records when the job was dead-lettered
- `dead_reason` records why (e.g., `max_retries_exhausted` or `retry_disabled`)
- `error_text` retains the most recent failure message

DLQ behavior provides:
- a stable terminal state for permanently failing jobs
- better operator visibility (what failed, why, and when)
- a place to build “requeue” or “inspect error” workflows in dashboards

---

### At-least-once delivery and idempotency

OpenQueue is designed for **at-least-once** execution.

This means a job may be executed more than once in rare cases, for example:
- a worker continues processing after its lease expires
- network failure prevents ack from reaching the server, and job is re-leased

Therefore, worker handlers should be **idempotent** (safe to run more than once), or you should introduce idempotency keys / de-duplication at the application level.

---

## System architecture

High level components:

1. **FastAPI service**
   - authenticates users via API token
   - exposes producer endpoints (enqueue, status, list, cancel)
   - exposes worker endpoints (lease, ack, nack)
   - exposes dashboard endpoints (queue stats)

2. **PostgreSQL**
   - stores users and jobs
   - provides locking semantics via `FOR UPDATE SKIP LOCKED`

3. **Workers (user-run)**
   - pull jobs via HTTP
   - execute workload
   - report completion/failure

---

## Database model

### users table (tenants)

A user is authenticated by API token:
- clients send `Authorization: Bearer <token>`
- server computes `sha256(token)` and matches against `users.api_token_hash`

Key fields:
- `id`
- `api_token_hash` (unique)
- `is_active`
- timestamps

### jobs table (queue items)

Jobs belong to a user (multi-tenancy):
- every query scopes by `user_id`

Key fields:
- `id` UUID
- `user_id` UUID (FK)
- `queue_name` TEXT
- `payload` JSONB
- `status` TEXT
- `priority` INT
- `retry_count`, `max_retries`
- timestamps: `created_at`, `updated_at`, `started_at`, `finished_at`
- leasing: `locked_by`, `locked_until`, `lease_token`
- scheduling: `run_at`
- output: `result` JSONB, `error_text` TEXT

---

## Queue algorithm (SQL-level)

### Leasing safely

Leasing is implemented using:

- `SELECT ... FOR UPDATE SKIP LOCKED` to safely pick a job without blocking other workers
- an update that marks the job `processing` and sets lease metadata

Eligibility rules (conceptual):
- `(status = 'pending' AND run_at <= NOW())`
- OR `(status = 'processing' AND locked_until < NOW())`  ← visibility timeout recovery

Ordering rules:
- higher `priority` first
- oldest `created_at` first (FIFO within priority)

When a job is leased:
- `status` set to `processing`
- `lease_token` set to a new UUID
- `locked_until` set to `NOW() + lease_seconds`
- `locked_by` set to the worker id
- `started_at` set on first processing start

### Acknowledging safely

ACK:
- update only succeeds if:
  - job is `processing`
  - `lease_token` matches
  - `user_id` matches

This prevents stale or unauthorized updates.

### Negative acknowledgement safely

NACK:
- first checks job is `processing` and token matches (often in a transaction)
- decides whether to requeue or fail based on retries
- clears lease metadata so job can be re-leased

---

## API surface (high level)

OpenQueue exposes three groups of endpoints:

### Producer API (clients)
- enqueue jobs
- query status and details
- list jobs for dashboards
- cancel pending jobs

### Worker API (BYOW)
- lease next job from a queue
- ack a leased job with result
- nack a leased job with error and retry preference

### Dashboard API
- queue stats per tenant (counts per status)

OpenAPI documentation is available at `/docs` and `/openapi.json`.

---

## Operational considerations

### Connection pooling
OpenQueue uses an async connection pool to Postgres. For production:
- tune pool size for your expected concurrency
- use statement timeouts and sensible server-side limits

### Indexing
Leasing and listing benefit from indexes. For production scale, ensure there is an index that supports:
- `(user_id, queue_name, status, run_at, priority, created_at)`

### Data retention
Completed jobs can accumulate quickly. Production deployments typically:
- delete old completed jobs after N days
- archive results separately if needed

### Rate limiting and quotas
A hosted queue must protect itself from abusive traffic:
- limit enqueue rate
- cap queue depth per tenant
- cap payload size

### Observability
Production systems need:
- structured logs (job_id, user_id, worker_id)
- metrics (queue depth, throughput, latency, failures)
- readiness checks that verify DB connectivity

---

## Production readiness checklist

OpenQueue becomes production-ready when it has:

1. **Correctness**
   - visibility timeout recovery (implemented)
   - heartbeat/lease extension for long jobs (recommended)
   - strong state machine constraints (recommended)

2. **Safety**
   - payload size limits
   - rate limiting / quotas
   - secure token derivation (ideally HMAC-based)

3. **Operations**
   - migrations (Alembic, versioned)
   - metrics + logs + tracing
   - readiness probes

4. **Quality**
   - integration tests (especially concurrency leasing tests)
   - load testing and index tuning

---

## Glossary

- **Producer**: client that enqueues jobs.
- **Worker**: process that leases and executes jobs.
- **Lease**: temporary claim on a job with expiry.
- **Lease token**: required to ack/nack a job; prevents stale updates.
- **Visibility timeout**: mechanism to recover jobs from crashed workers.
- **ACK**: acknowledge completion.
- **NACK**: negative acknowledge (failure); may requeue or fail.
- **Idempotency**: ability to safely run a job more than once.

---

## Final note

OpenQueue is intentionally simple: it builds queue semantics on top of Postgres primitives (locking + transactional updates). This makes it easy to understand, audit, and operate. As the project evolves, the recommended direction is to add reliability features (heartbeats, backoff, DLQ), operational safeguards (quotas), and observability (metrics) without sacrificing the clarity of the underlying SQL model.