# OpenQueue

OpenQueue is a hosted, Postgres-backed job queue service designed to replace Redis-backed queues for many workloads.

- **Producers** enqueue jobs via a REST API.
- **Workers (BYOW: Bring Your Own Worker)** lease jobs for processing and report completion/failure with `ack`/`nack`.
- **Multi-tenant by design**: every job belongs to a user, identified via API token authentication.

> Status: early-stage but functional. Contributions welcome.

---

## Table of Contents

- [Features](#features)
- [Concepts](#concepts)
- [Architecture](#architecture)
- [Requirements](#requirements)
- [Quickstart (Docker Compose)](#quickstart-docker-compose)
- [Quickstart (Local / Virtualenv)](#quickstart-local--virtualenv)
- [Migrations (Alembic)](#migrations-alembic)
- [Database Schema](#database-schema)
- [Authentication](#authentication)
  - [Token hashing strategy (SHA vs HMAC)](#token-hashing-strategy-sha-vs-hmac)
  - [Create a User / API Token](#create-a-user--api-token)
  - [Default Admin Seed (Dev)](#default-admin-seed-dev)
- [API Overview](#api-overview)
  - [Producer API (Clients)](#producer-api-clients)
  - [Worker API (BYOW)](#worker-api-byow)
  - [Observability](#observability)
  - [Dashboard API](#dashboard-api)
- [Testing](#testing)
- [Operational Notes](#operational-notes)
- [Production Notes](#production-notes)
- [Development Notes](#development-notes)
- [Roadmap](#roadmap)
- [License](#license)

---

## Features

- Postgres-backed job storage (JSONB payload/result)
- Job priorities (higher number = higher priority)
- Multi-tenant support via `users` + API tokens
- Worker leasing with a `lease_token`
- Visibility-timeout recovery (re-lease expired processing jobs)
- Lease renewal for long-running jobs (`heartbeat`)
- `ack` / `nack` semantics
- Retry backoff via `run_at` scheduling
- Dead-letter queue (DLQ) state (`dead`)
- Dashboard endpoints for queue stats and job listing
- OpenAPI/Swagger documentation
- Prometheus metrics endpoint (`GET /metrics`)
- Readiness endpoint (`GET /ready`)
- Basic per-tenant rate limiting (in-memory token bucket; per-process)

---

## Concepts

### Job statuses

OpenQueue uses a `status` field (text) with the following values:

- `pending` — queued and waiting
- `processing` — leased by a worker
- `completed` — successfully finished
- `failed` — failed (legacy/compat; DLQ uses `dead`)
- `cancelled` — cancelled before processing
- `dead` — dead-letter queue (retries exhausted or retry disabled)

### Lease tokens

Workers claim jobs using `lease`. The server returns a `lease_token` which must be provided when acknowledging completion (`ack`), failure (`nack`), or extending a lease (`heartbeat`).

This prevents:
- two workers from acking the same job
- acking a job you didn’t lease
- stale workers from updating a job after the lease was reassigned

---

## Architecture

- **API**: FastAPI + Uvicorn
- **DB**: PostgreSQL
- **DB Driver**: `asyncpg`

Core idea: the queue is implemented using Postgres row locking (`FOR UPDATE SKIP LOCKED`) to safely lease jobs with concurrent workers.

---

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