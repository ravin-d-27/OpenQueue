# OpenQueue — Concept & Technical Documentation

OpenQueue is a hosted, PostgreSQL-backed job queue service designed to replace Redis-backed queues for many workloads. It provides a clean HTTP API for **producers** (clients that enqueue work) and **workers** (processes that execute work). OpenQueue is built around a simple idea:

> A queue is a table of jobs. Workers safely "lease" jobs using database row locking, then **ack** (success) or **nack** (failure) with a lease token.

This document explains the *why*, the *how*, and the technical details so a new contributor or user can understand the project end-to-end.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OpenQueue System                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐                     ┌────────────────────────────────┐  │
│  │   Producer   │                     │           Workers              │  │
│  │  (Client)    │                     │      (User-run processes)       │  │
│  └──────┬───────┘                     └─────────────┬──────────────────┘  │
│         │                                        │                         │
│         │  HTTP API                              │  HTTP API               │
│         │                                        │                         │
│         ▼                                        ▼                         │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │                     FastAPI Application                      │          │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │          │
│  │  │  Jobs Router │  │ Workers      │  │  Dashboard       │  │          │
│  │  │  (enqueue,   │  │  Router      │  │  Router         │  │          │
│  │  │   status,    │  │  (lease,     │  │  (stats)        │  │          │
│  │  │   list,      │  │   ack,       │  │                  │  │          │
│  │  │   cancel)    │  │   nack,      │  │                  │  │          │
│  │  │              │  │   heartbeat) │  │                  │  │          │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘  │          │
│  │           │                │                   │             │          │
│  │           └────────────────┴───────────────────┘             │          │
│  │                          │                                   │          │
│  │                    ┌─────▼─────┐                             │          │
│  │                    │  Service  │                             │          │
│  │                    │  Layer    │                             │          │
│  │                    │ (jobs_    │                             │          │
│  │                    │ service)  │                             │          │
│  │                    └─────┬─────┘                             │          │
│  │                          │                                   │          │
│  │                    ┌─────▼─────┐                             │          │
│  │                    │   CRUD    │                             │          │
│  │                    │   Layer   │                             │          │
│  │                    └─────┬─────┘                             │          │
│  └──────────────────────────┼───────────────────────────────────┘          │
│                             │                                              │
│                             ▼                                              │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │                    PostgreSQL Database                        │          │
│  │                                                               │          │
│  │  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐   │          │
│  │  │   Users     │   │    Jobs     │   │   Indexes       │   │          │
│  │  │  Table      │   │   Table     │   │   (hot paths)   │   │          │
│  │  │             │   │             │   │                 │   │          │
│  │  │ • id        │   │ • id        │   │ • lease path    │   │          │
│  │  │ • email     │   │ • queue_name│   │ • recovery      │   │          │
│  │  │ • api_token │   │ • payload   │   │ • DLQ listing  │   │          │
│  │  │   _hash     │   │ • status    │   │                 │   │          │
│  │  │ • is_active │   │ • priority  │   │                 │   │          │
│  │  └─────────────┘   │ • run_at    │   └─────────────────┘   │          │
│  │                     │ • lease_*    │                         │          │
│  │                     │ • result     │                         │          │
│  │                     │ • error_text │                         │          │
│  │                     └─────────────┘                         │          │
│  │                                                               │          │
│  └───────────────────────────────────────────────────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Codebase Components

### Directory Structure

```
OpenQueue/
├── app/                          # Main FastAPI application
│   ├── __init__.py
│   ├── main.py                   # Entry point
│   ├── fastapi_app.py            # ASGI app factory
│   ├── app_factory.py            # App configuration
│   ├── auth.py                   # Token-based authentication
│   ├── database.py               # Database connection pool
│   ├── settings.py               # Configuration management
│   ├── crud.py                   # Database operations (500+ lines)
│   ├── models.py                 # Pydantic request/response models
│   ├── deps.py                   # Dependency injection
│   ├── rate_limit.py             # Token bucket rate limiting
│   ├── middleware.py             # Request/response middleware
│   ├── metrics.py                # Prometheus metrics
│   ├── maintenance.py            # Background maintenance tasks
│   │
│   ├── routers/                  # API route handlers
│   │   ├── __init__.py
│   │   ├── jobs.py               # Producer endpoints
│   │   ├── workers.py            # Worker endpoints
│   │   ├── dashboard.py          # Stats endpoints
│   │   └── observability.py      # Health/readiness
│   │
│   └── services/                 # Business logic layer
│       ├── __init__.py
│       └── jobs_service.py       # Job operations
│
├── sdk/                          # Client SDKs
│   └── python/                   # Python SDK
│       ├── openqueue/            # Main package
│       │   ├── __init__.py
│       │   ├── client.py         # OpenQueue client
│       │   ├── models.py         # Data models
│       │   └── exceptions.py     # Custom exceptions
│       ├── tests/                # SDK tests
│       ├── examples/             # Usage examples
│       └── pyproject.toml        # Package config
│
├── migrations/                   # Alembic database migrations
├── tests/                        # Integration tests
├── docker-compose.yml            # Local development
├── Dockerfile                    # Production container
├── schema.sql                   # Initial database schema
├── requirements.txt              # Python dependencies
└── alembic.ini                  # Migration config
```

### Component Details

#### 1. FastAPI Application (`app/`)

The core backend service built with FastAPI:

| File | Purpose |
|------|---------|
| `main.py` | Application entry point |
| `app_factory.py` | Creates and configures the FastAPI app |
| `auth.py` | Token-based authentication (SHA-256 hashing) |
| `database.py` | PostgreSQL connection pool management |
| `settings.py` | Environment configuration |
| `crud.py` | Database operations (create, read, update, delete) |
| `models.py` | Pydantic models for requests/responses |
| `deps.py` | FastAPI dependencies (auth, rate limiting) |
| `rate_limit.py` | In-memory token bucket rate limiting |
| `middleware.py` | Request logging, request ID tracking |
| `metrics.py` | Prometheus metrics exporters |
| `maintenance.py` | Background job cleanup and lease reaping |

#### 2. API Routers (`app/routers/`)

```
jobs.py          → Producer API
├── POST   /jobs              - Enqueue a job
├── GET    /jobs/{job_id}     - Get job status
├── GET    /jobs/{job_id}/detail - Get full job details
├── GET    /jobs              - List jobs (with filters)
├── POST   /jobs/batch       - Batch enqueue
└── POST   /jobs/{job_id}/cancel - Cancel pending job

workers.py       → Worker API (BYOW - Bring Your Own Worker)
├── POST   /queues/{queue_name}/lease      - Lease next job
├── POST   /jobs/{job_id}/ack               - Acknowledge completion
├── POST   /jobs/{job_id}/nack             - Negative acknowledge (failure)
└── POST   /jobs/{job_id}/heartbeat         - Extend lease (heartbeat)

dashboard.py     → Monitoring API
└── GET   /dashboard/queues - Get queue statistics

observability.py → Health checks
├── GET   /health   - Liveness probe
└── GET   /ready    - Readiness probe
```

#### 3. Service Layer (`app/services/`)

- `jobs_service.py`: Business logic for job operations, orchestrates CRUD calls

#### 4. Python SDK (`sdk/python/`)

```
openqueue/
├── client.py       # Main OpenQueue class
│                   # - Producer: enqueue, get_status, get_job, list_jobs, cancel_job
│                   # - Worker: lease, ack, nack, heartbeat
│                   # - Dashboard: get_queue_stats
├── models.py       # Data classes (Job, LeasedJob, QueueStats, JobListResponse)
└── exceptions.py   # Custom exceptions (JobNotFoundError, LeaseTokenError, etc.)
```

---

## Database Schema

### Users Table (Tenants)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    api_token_hash TEXT NOT NULL UNIQUE,  -- SHA-256 of API token
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMP
);
```

### Jobs Table (Queue Items)

```sql
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,              -- Multi-tenancy
    queue_name TEXT NOT NULL,           -- Queue identifier
    payload JSONB NOT NULL,              -- Job data

    -- Status lifecycle
    status TEXT NOT NULL DEFAULT 'pending',  -- pending→processing→completed
                                                -- pending→cancelled
                                                -- processing→failed→dead

    priority INTEGER NOT NULL DEFAULT 0,   -- Higher = more urgent

    -- Retry configuration
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,

    -- Scheduling (run_at for delayed jobs)
    run_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Leasing / visibility timeout
    locked_until TIMESTAMP,              -- Lease expiry
    locked_by TEXT,                      -- Worker ID
    lease_token UUID,                   -- Required for ack/nack

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP,
    finished_at TIMESTAMP,

    -- Results
    result JSONB,                        -- Completion result
    error_text TEXT,                     -- Failure message

    -- Dead-letter queue
    dead_at TIMESTAMP,
    dead_reason TEXT,

    -- Metadata
    lease_lost_count INTEGER NOT NULL DEFAULT 0
);
```

### Key Indexes (Hot Paths)

```sql
-- Lease: find next eligible pending job
CREATE INDEX idx_jobs_user_queue_pending_ready
    ON jobs(user_id, queue_name, run_at, priority DESC, created_at)
    WHERE status = 'pending';

-- Recovery: re-lease expired processing jobs
CREATE INDEX idx_jobs_user_queue_processing_expired
    ON jobs(user_id, queue_name, locked_until)
    WHERE status = 'processing';

-- DLQ: list dead jobs
CREATE INDEX idx_jobs_user_queue_dead
    ON jobs(user_id, queue_name, dead_at)
    WHERE status = 'dead';
```

---

## Job Lifecycle

```
                    ┌──────────────┐
                    │   PENDING    │◄─────────────────────────────┐
                    │  (queued)    │                              │
                    └──────┬───────┘                              │
                           │                                       │
                           │ lease()                               │
                           ▼                                       │
                    ┌──────────────┐         ┌──────────────┐      │
                    │  PROCESSING  │         │   CANCELLED  │      │
                    │  (leased)    │         │  (by user)   │      │
                    └──────┬───────┘         └──────────────┘      │
                           │                                       │
              ┌────────────┴────────────┐                         │
              │                         │                         │
              │ ack()                   │ nack(retry=true)       │
              │ (success)               │ (failure + retry)      │
              ▼                         ▼                         │
     ┌─────────────────┐      ┌──────────────────┐                │
     │   COMPLETED     │      │    FAILED        │                │
     │  (done)        │      │  (will retry)    │                │
     └─────────────────┘      └────────┬─────────┘                │
                                      │                           │
                               retry available?                   │
                                      │ (yes)                    │
                                      └──────────────────────────►│
                                                                   
                    ┌──────────────┐
                    │     DEAD     │ (DLQ - no more retries)
                    │  (permanent) │
                    └──────────────┘
```

---

## Core Concepts

### 1. Leasing with Row Locking

Workers safely claim jobs using PostgreSQL's `FOR UPDATE SKIP LOCKED`:

```sql
-- Atomically claim a job without blocking other workers
UPDATE jobs
SET status = 'processing',
    locked_until = NOW() + interval '30 seconds',
    lease_token = gen_random_uuid(),
    locked_by = $worker_id,
    started_at = COALESCE(started_at, NOW())
WHERE id = (
    SELECT id FROM jobs
    WHERE user_id = $user_id
      AND queue_name = $queue_name
      AND status = 'pending'
      AND run_at <= NOW()
    ORDER BY priority DESC, created_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
RETURNING *;
```

### 2. Visibility Timeout (Recovery)

Jobs stuck in `processing` become available again when lease expires:

```sql
-- Recover stuck jobs (visibility timeout)
SELECT id FROM jobs
WHERE status = 'processing'
  AND locked_until < NOW()
ORDER BY priority DESC, created_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED;
```

### 3. Heartbeat (Lease Renewal)

Workers extend leases for long-running jobs:

```sql
UPDATE jobs
SET locked_until = NOW() + interval '30 seconds'
WHERE id = $job_id
  AND lease_token = $lease_token
  AND status = 'processing';
```

### 4. Retry with Backoff

Failed jobs are requeued with exponential backoff:

```sql
UPDATE jobs
SET status = 'pending',
    retry_count = retry_count + 1,
    run_at = NOW() + (2 ^ retry_count) * interval '1 second',  -- 1, 2, 4, 8...
    locked_until = NULL,
    lease_token = NULL,
    locked_by = NULL
WHERE id = $job_id;
```

---

## API Usage Examples

### Producer (Enqueue Jobs)

```python
from openqueue import OpenQueue

client = OpenQueue("http://localhost:8000", "your-api-token")

# Simple job
job_id = client.enqueue(
    queue_name="emails",
    payload={"to": "user@example.com", "subject": "Hello"}
)

# Scheduled job (run later)
job_id = client.enqueue(
    queue_name="reminders",
    payload={"user_id": 123, "message": "Reminder!"},
    run_at="2026-01-01T09:00:00Z"
)

# Batch enqueue
job_ids = client.enqueue_batch([
    {"queue_name": "emails", "payload": {"to": "a@b.com"}},
    {"queue_name": "emails", "payload": {"to": "c@d.com"}, "priority": 10},
])
```

### Worker (Process Jobs)

```python
from openqueue import OpenQueue

client = OpenQueue("http://localhost:8000", "your-api-token")

while True:
    leased = client.lease(queue_name="emails", worker_id="worker-1")
    
    if leased:
        try:
            # Process job
            payload = leased.job.payload
            print(f"Processing: {payload}")
            
            # Success
            client.ack(leased.job.id, leased.lease_token, result={"done": True})
        except Exception as e:
            # Failure - retry
            client.nack(leased.job.id, leased.lease_token, error=str(e))
```

---

## Production Readiness

### ✅ Implemented Features

| Feature | Description |
|---------|-------------|
| **Leasing with row locking** | `FOR UPDATE SKIP LOCKED` prevents duplicate processing |
| **Visibility timeout recovery** | Stuck jobs auto-recovered after lease expiry |
| **Heartbeat/lease renewal** | Long-running jobs stay leased |
| **ACK/NACK with tokens** | Prevents stale worker updates |
| **Retry backoff** | Exponential backoff prevents retry storms |
| **Dead-letter queue** | Permanent failures isolated |
| **Database constraints** | Status enum, retry bounds |
| **Indexes** | Optimized hot paths |
| **Alembic migrations** | Safe schema evolution |
| **Request IDs** | Traceable logs |
| **Prometheus metrics** | Observability |
| **Rate limiting** | Per-instance protection |
| **Health checks** | Liveness/readiness probes |

### 🔧 Recommended Additions for Production

| Feature | Priority |
|---------|----------|
| Distributed rate limiting | High |
| API key rotation | High |
| Job attempt audit trail | High |
| Integration tests | High |
| DB connection tuning | Medium |
| Payload size limits | Medium |
| API versioning | Low |

---

## Glossary

- **Producer**: Client that enqueues jobs
- **Worker**: Process that leases and executes jobs
- **Lease**: Temporary claim on a job with expiry
- **Lease Token**: Required for ack/nack; prevents stale updates
- **Visibility Timeout**: Auto-recovers jobs from crashed workers
- **ACK**: Successful completion
- **NACK**: Failure (may retry or go to DLQ)
- **DLQ**: Dead-letter queue for permanent failures
- **Idempotency**: Safe to execute more than once

---

## Final Note

OpenQueue is intentionally simple: it builds queue semantics on top of Postgres primitives (locking + transactional updates). This makes it easy to understand, audit, and operate.
