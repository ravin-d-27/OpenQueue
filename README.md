## OpenQueue

OpenQueue is a hosted, Postgres‑backed job queue service designed to replace Redis‑backed queues for many workloads.

- **Producers** enqueue jobs via a REST API.
- **Workers (BYOW: Bring Your Own Worker)** lease jobs for processing and report completion/failure with `ack`/`nack`.
- **Multi‑tenant by design**: every job belongs to a user, identified via API token authentication.

By default (in local/dev), OpenQueue seeds an admin user in the database with the following API token:

- **Bearer token:** `oq_live_qXxA5liMxzRhz3uVTFYziaQSrw8tB05y2hU5O7VivyA`

Use it like:

- `Authorization: Bearer oq_live_qXxA5liMxzRhz3uVTFYziaQSrw8tB05y2hU5O7VivyA`

You can rotate/change this later by inserting a new row in `users` (with the correct token hash) and disabling/removing this seed in production.

---

## When to Use OpenQueue vs Redis

### Use OpenQueue When:

| Scenario | Why OpenQueue |
|----------|---------------|
| **You need durability and inspectability** | Jobs are rows in Postgres - query, debug, and audit with standard SQL |
| **You already use Postgres** | No additional infrastructure - fewer moving pieces |
| **Building a multi-tenant SaaS** | Built-in tenant isolation with API tokens |
| **Compliance/audit requirements** | Job history in relational DB, can join with other tables |
| **Simpler operations** | One database to manage instead of Redis + queue patterns |
| **Medium throughput needs** | 100s-1000s jobs/sec is manageable with proper indexing |

### Use Redis When:

| Scenario | Why Redis |
|----------|-----------|
| **Ultra-low latency required** | In-memory, sub-millisecond operations |
| **Very high throughput** | 10,000+ jobs/sec |
| **Real-time caching** | Cache-heavy workloads |
| **Pub/Sub patterns** | Real-time messaging between services |
| **Existing Redis infrastructure** | Already mature ops tooling |

### Example Decision:

```python
# ✅ Use OpenQueue for: Processing user signups
# - Need to audit/track each signup attempt
# - Medium volume (100 signups/min)
# - Need retry logic for failed signups
# - Want dashboard visibility into queue depth

job_id = client.enqueue(
    queue_name="user-signups",
    payload={"user_id": 123, "email": "user@example.com"}
)

# ⚡ Use Redis for: Caching user sessions
# - Microsecond latency needed
# - Ephemeral data
# - High volume
redis.set(f"session:{user_id}", data, ex=3600)
```

---

## Why PostgreSQL Schema?

We chose PostgreSQL with this specific schema design for several reasons:

### 1. Single Source of Truth

```sql
-- All job state in one place
jobs (
    id, user_id, queue_name, payload, status,
    priority, retry_count, max_retries, run_at,
    locked_until, locked_by, lease_token,
    result, error_text, dead_at, dead_reason
)
```

**Why:** No need for separate "queue store" + "result store" + "retry store". Everything is in one table.

### 2. JSONB for Flexible Payloads

```sql
payload JSONB NOT NULL,    -- Flexible job data
result JSONB,              -- Flexible result data
```

**Why:**
- Store any JSON structure without schema changes
- Can query inside JSON with Postgres operators
- Efficient binary storage

### 3. Visibility Timeout via `locked_until`

```sql
locked_until TIMESTAMP,    -- When lease expires
lease_token UUID,          -- Prevents stale updates
```

**Why:**
- Workers crash? Job auto-recovers when `locked_until < NOW()`
- No need for external "stuck job" detection
- Lease tokens prevent zombie workers from ack/nack

### 4. Scheduling with `run_at`

```sql
run_at TIMESTAMP NOT NULL DEFAULT NOW(),
```

**Why:**
- Delayed jobs: `run_at = NOW() + 1 hour`
- Retry backoff: `run_at = NOW() + exponential_backoff`
- Single field handles both cases

### 5. Dead Letter Queue (DLQ)

```sql
status = 'dead',
dead_at TIMESTAMP,
dead_reason TEXT,
```

**Why:**
- Permanent failures don't block the queue
- Debug: `SELECT * FROM jobs WHERE status = 'dead'`
- Can build "requeue" UI from DLQ

### 6. Multi-Tenancy with `user_id`

```sql
user_id UUID REFERENCES users(id) ON DELETE CASCADE
```

**Why:**
- Complete tenant isolation
- Row-level security
- Per-tenant queue statistics

---

## Real-World Use Cases

### 1. Email Processing Pipeline

```
User Action → OpenQueue → Worker → Send Email → ACK
```

```python
# Producer: User registers
client.enqueue(
    queue_name="welcome-emails",
    payload={"user_id": 123, "template": "welcome"}
)

# Worker: Processes emails
while True:
    job = client.lease("welcome-emails", "email-worker-1")
    send_email(job.payload["template"], job.payload["user_id"])
    client.ack(job.id, lease_token)
```

**Why this pattern:**
- Decouple user signup (fast) from email sending (slow)
- Retry failed sends automatically
- Don't lose emails if email service is down

### 2. Background Data Processing

```
Upload CSV → Enqueue row processing jobs → Multiple Workers → Results
```

```python
# Producer: Upload handler
for row in csv_reader:
    client.enqueue(
        queue_name="process-rows",
        payload={"row_id": row.id, "data": row.data}
    )

# Workers: Process in parallel
job = client.lease("process-rows", "worker-1")
process_row(job.payload)
client.ack(job.id, lease_token, result={"processed": True})
```

**Why this pattern:**
- Handle large files without timeout
- Parallel processing scales automatically
- Failed rows retry without blocking others

### 3. Event-Driven Architecture (EDA)

OpenQueue is ideal for EDA workloads where you need **at-least-once delivery**:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Service A │────▶│  OpenQueue  │────▶│  Service B  │
│  (Producer) │     │   (Queue)   │     │  (Worker)   │
└─────────────┘     └─────────────┘     └─────────────┘
```

#### Example: Order Processing Pipeline

```python
# Service A: Order Service (Producer)
@app.post("/orders")
async def create_order(order: Order):
    # Save order first
    db.save(order)
    
    # Queue processing - don't block user response
    openqueue.enqueue(
        queue_name="order-processing",
        payload={
            "order_id": order.id,
            "customer_email": order.email,
            "items": order.items
        }
    )
    
    return {"order_id": order.id, "status": "processing"}
```

```python
# Service B: Notification Worker
while True:
    job = openqueue.lease("order-processing", "notification-worker")
    
    # Send notification
    try:
        send_notification(
            to=job.payload["customer_email"],
            template="order_confirmed",
            data=job.payload
        )
        openqueue.ack(job.id, job.lease_token)
    except Exception as e:
        # Retry with backoff
        openqueue.nack(job.id, job.lease_token, error=str(e))
```

#### Example: EDA Event Handlers

```python
# Event: Payment Completed
client.enqueue(
    queue_name="payment-events",
    payload={
        "event_type": "payment.completed",
        "order_id": "12345",
        "amount": 99.99,
        "timestamp": "2026-03-05T10:00:00Z"
    }
)

# Worker 1: Update inventory
client.enqueue(
    queue_name="inventory-events", 
    payload={"event": "payment.completed", "order_id": "12345"}
)

# Worker 2: Send receipt
client.enqueue(
    queue_name="receipt-events",
    payload={"event": "payment.completed", "order_id": "12345"}
)

# Worker 3: Update analytics
client.enqueue(
    queue_name="analytics-events",
    payload={"event": "payment.completed", "order_id": "12345"}
)
```

**Why OpenQueue for EDA:**

| EDA Requirement | OpenQueue Feature |
|-----------------|-------------------|
| **Decouple services** | Async job processing |
| **Handle bursts** | Queue absorbs traffic spikes |
| **Reliability** | Visibility timeout + retries |
| **Ordering** | Priority + FIFO within priority |
| **Debugging** | Query job history in SQL |
| **Multi-tenant** | Built-in tenant isolation |

### 4. Webhooks & External APIs

```python
# Producer: User triggers action
client.enqueue(
    queue_name="webhook-delivery",
    payload={
        "url": "https://example.com/webhook",
        "event": "user.created",
        "data": user_data
    },
    max_retries=5
)
```

**Why:**
- External APIs may be slow/unavailable
- Retry with exponential backoff
- Don't block user requests

### 5. Scheduled Tasks

```python
# Schedule for later
import datetime
run_at = (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).isoformat()

client.enqueue(
    queue_name="daily-reports",
    payload={"report_type": "sales", "date": "2026-03-05"},
    run_at=f"{run_at}Z"
)
```

**Why:**
- No cron needed - OpenQueue handles scheduling
- Missed runs? Job sits in queue until processed
- Can pause/resume by changing `run_at`

---

## The Producer-Consumer Pattern

The producer-consumer pattern is fundamental to OpenQueue:

```
Producer (enqueue)    →    Queue    →    Consumer (lease + process)
     │                                  │
     │  1. Creates work                  │  3. Claims work
     │  2. Defines what to do            │  4. Does the work
     │                                   │  5. Reports success/failure
     ▼                                   ▼
  Fast response                     Scalable workers
  to caller
```

### Why This Pattern Works:

1. **Decoupling**: Producers don't wait for work to complete
2. **Scalability**: Add workers as load increases
3. **Reliability**: Jobs persist even if workers crash
4. **Resilience**: Retries handle transient failures
5. **Visibility**: Query queue state for debugging

---

### Features (high level)

- PostgreSQL‑backed job storage (JSONB payload/result).
- Job priorities; per‑tenant queues.
- Worker leasing with `lease_token`, visibility‑timeout recovery, heartbeat.
- Retries with backoff and a dead‑letter queue (`dead` status).
- Dashboard/statistics endpoints.
- OpenAPI/Swagger docs, Prometheus metrics (`/metrics`), health/readiness (`/health`, `/ready`).

---

### Requirements

- **Python**: 3.11+ (CI and Docker use Python 3.13).
- **PostgreSQL**: 14+ recommended.
- **Python deps**: installed from `requirements.txt`.

---

### Quickstart (Docker Compose)

This is the easiest way to run OpenQueue locally.

#### 1) Start services

From the project root:

```bash
docker compose up --build
```

Services:

- `openqueue-db` (Postgres)
- `openqueue-api` (FastAPI)

#### 2) Open docs

- `http://127.0.0.1:8000/docs`

#### 3) Authentication

All endpoints (except health/ready/metrics) require:

- `Authorization: Bearer <token>`

For how to create tokens and users, see `BEGINNER_GUIDE.md` or `Concept.md` (Authentication sections).

#### Resetting the DB (dev only)

If you changed the schema and want a clean boot:

```bash
docker compose down -v
docker compose up --build
```

This deletes the database volume.

---

### Quickstart (Local / Virtualenv)

#### 1) Create and activate venv

```bash
python -m venv venv
. venv/bin/activate
```

#### 2) Install dependencies

```bash
pip install -r requirements.txt
```

#### 3) Configure environment

Create a `.env` file:

```bash
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
OPENQUEUE_TOKEN_HMAC_SECRET=change-me   # recommended in production
```

Important:

- If your password contains special characters like `@`, you must URL‑encode them (e.g. `@` → `%40`).

#### 4) Run the API

```bash
uvicorn app.fastapi_app:app --reload
```

Then browse `http://127.0.0.1:8000/docs`.

---

### Migrations (Alembic)

OpenQueue uses Alembic for schema migrations.

From the project root (with `DATABASE_URL` set):

```bash
alembic upgrade head
```

To create a new migration:

```bash
alembic revision -m "describe your change"
```

For more context on the schema, see `Concept.md` (Database model).

---

### Testing

Integration tests require `DATABASE_URL` pointing to a running Postgres:

```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/openqueue
pytest -q
```

There is a notable concurrency test (`tests/test_concurrency_leasing.py`) that ensures no duplicate leases under parallel workers.

---

### License

See `LICENSE`.

## Requirements

### Runtime

- Python 3.11+ recommended (Docker image uses Python 3.13)
- PostgreSQL 14+ recommended

### Python dependencies

Installed from `requirements.txt` (FastAPI, Uvicorn, asyncpg, Prometheus client, pytest, etc).

---

## Quickstart (Docker Compose)

This is the easiest way to run OpenQueue locally.

### 1) Start services

From the project root:

```OpenQueue/README.md#L1-260
docker compose up --build
```

Services:
- `openqueue-db` (Postgres)
- `openqueue-api` (FastAPI)

### 2) Open docs

- http://127.0.0.1:8000/docs

### 3) Authentication

All endpoints require:

- `Authorization: Bearer <token>`

See [Authentication](#authentication).

> Note: If you run Postgres via Docker Compose and mount `schema.sql` into `docker-entrypoint-initdb.d/`, initialization only runs on first boot of an empty volume. For real deployments, use Alembic migrations.

### Resetting the DB (dev only)

If you changed the schema and want a clean boot:

```OpenQueue/README.md#L1-260
docker compose down -v
docker compose up --build
```

This deletes the database volume.

---

## Quickstart (Local / Virtualenv)

### 1) Create and activate venv

```OpenQueue/README.md#L1-260
python -m venv venv
. venv/bin/activate
```

### 2) Install deps

```OpenQueue/README.md#L1-260
pip install -r requirements.txt
```

### 3) Configure environment

Create `.env`:

```OpenQueue/README.md#L1-260
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME
OPENQUEUE_TOKEN_HMAC_SECRET=change-me   # recommended in production
```

Important:
- If your password contains special characters like `@`, you must URL-encode them (e.g. `@` → `%40`).

### 4) Run API

```OpenQueue/README.md#L1-260
uvicorn app.fastapi_app:app --reload
```

---

## Migrations (Alembic)

OpenQueue includes Alembic and an initial migration to make schema changes repeatable.

### Apply migrations

From the project root (with `DATABASE_URL` set):

```OpenQueue/README.md#L1-260
alembic upgrade head
```

### Create a new migration

```OpenQueue/README.md#L1-260
alembic revision -m "describe your change"
```

> Note: This project uses SQL-first migrations (no ORM autogenerate).

---

## Database Schema

Schema exists in two forms:
- `schema.sql` for local initialization
- Alembic migrations under `migrations/` for real deployments

OpenQueue expects `jobs` to include:
- leasing: `locked_until`, `locked_by`, `lease_token`
- scheduling: `run_at`
- metadata: `started_at`, `finished_at`
- DLQ: `dead_at`, `dead_reason`

---

## Authentication

OpenQueue uses **API tokens**.

- Clients send: `Authorization: Bearer <token>`
- Server derives a lookup hash and checks it against `users.api_token_hash`
- You **never** store the raw token in Postgres

### Token hashing strategy (SHA vs HMAC)

By default, OpenQueue uses `sha256(token)`.

If `OPENQUEUE_TOKEN_HMAC_SECRET` is set, OpenQueue uses:
- `HMAC-SHA256(secret, token)`

HMAC is recommended for hosted production deployments because it reduces the risk of offline token-guessing if the database leaks.

### Create a user / API token

1) Generate a token and hash (SHA-256 example):

```OpenQueue/README.md#L1-260
python - <<'PY'
import secrets, hashlib
token = "oq_live_" + secrets.token_urlsafe(32)
token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
print("TOKEN:", token)
print("TOKEN_HASH:", token_hash)
PY
```

2) Insert into DB:

```OpenQueue/README.md#L1-260
INSERT INTO users (email, api_token_hash, is_active)
VALUES ('you@example.com', '<TOKEN_HASH>', TRUE)
RETURNING id, email, is_active, created_at;
```

3) Use the token (raw):

```OpenQueue/README.md#L1-260
Authorization: Bearer <TOKEN>
```

> If you enable HMAC hashing, make sure you compute and store the HMAC hash (not the plain SHA-256).

### Default admin seed (dev)

If you seed a dev admin in SQL, remember:

- Bearer token must be the **raw token**, not the hash.

---

## API Overview

All endpoints are authenticated unless otherwise noted.

### Producer API (Clients)

#### `POST /jobs` — Enqueue job

Request body:
- `queue_name` (string, default: `"default"`)
- `payload` (JSON object)
- `priority` (int, higher = higher priority)
- `max_retries` (int)

Response:
- `201 { job_id, status: "queued" }`

#### `GET /jobs/{job_id}` — Job status
Response: `{ job_id, status }`

#### `GET /jobs/{job_id}/detail` — Job details
Response: full `JobResponse`

#### `GET /jobs` — List jobs
Query:
- `queue_name` (optional)
- `status` (optional)
- `limit` (default 50, max 200)
- `offset` (default 0)

#### `POST /jobs/{job_id}/cancel` — Cancel job
Cancels only if job is still `pending`.

---

### Worker API (BYOW)

#### `POST /queues/{queue_name}/lease` — Lease next job
Request:
- `worker_id` (string)
- `lease_seconds` (int, default 30)

Response:
- `null` if no job available, or:
- `{ job, lease_token, lease_expires_at }`

Leasing rules:
- leases `pending` jobs where `run_at <= now()`
- can re-lease `processing` jobs where `locked_until < now()` (visibility-timeout recovery)

#### `POST /jobs/{job_id}/ack` — Acknowledge completion
Request:
- `lease_token`
- `result` (optional JSON object)

Response: `{ job_id, status: "completed" }`

#### `POST /jobs/{job_id}/nack` — Negative acknowledgement
Request:
- `lease_token`
- `error` (string)
- `retry` (bool, default true)

Behavior:
- If retries remain: requeue to `pending` and set `run_at` into the future (exponential backoff)
- Otherwise: move to DLQ (`dead`) and set `dead_at`/`dead_reason`

#### `POST /jobs/{job_id}/heartbeat` — Extend lease
Request:
- `lease_token`
- `lease_seconds` (optional)

Response:
- `{ job_id, status: "lease_extended" }`

---

### Observability

#### `GET /metrics`
Prometheus metrics endpoint.

#### `GET /health`
Liveness check.

#### `GET /ready`
Readiness check (DB connectivity).

---

### Dashboard API

#### `GET /dashboard/queues` — Per-queue statistics
Returns counts by status per queue for the authenticated user.

---

## Testing

### Run tests

Integration tests require `DATABASE_URL` pointing to a running Postgres:

```OpenQueue/README.md#L1-260
export DATABASE_URL=postgresql://user:pass@localhost:5432/openqueue
pytest -q
```

Notable tests:
- concurrency leasing test ensures no duplicate leases under parallel workers.

---

## Operational Notes

- **At-least-once processing**: Workers should be idempotent.
- **Lease expiry recovery**: expired leases can be recovered and re-leased.
- **Heartbeat**: required for long-running jobs to avoid re-leasing.
- **Retries**: retries use backoff via `run_at`.
- **DLQ**: permanent failures move to `dead`.

---

## Production Notes

### Rate limiting / quotas
OpenQueue includes basic in-memory rate limits for key actions. In a multi-replica deployment, replace with a distributed limiter at the API gateway or a shared store.

### Metrics & logging
- Prometheus metrics are exposed at `/metrics`.
- Request IDs are returned as `X-Request-ID`.
- Structured request logs include method/path/status/duration.

### Background maintenance
For retention cleanup and lease reaping at low traffic, run a maintenance process (recommended as a separate container/cronjob).

---

## Development Notes

- Prefer schema changes via Alembic migrations.
- Keep queue hot paths in SQL (locking + transactional updates).
- Avoid high-cardinality metric labels (do not label by job_id).

---

## Roadmap

High-priority next steps:
- Global (distributed) rate limiting across replicas
- Job attempt/audit trail table (`job_attempts`)
- API versioning (`/v1`)
- Maintenance runner integration as a separate service
- Performance tuning under load (indexes + query plans)

---

## License

See `LICENSE`.