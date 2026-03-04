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
- [Database Schema](#database-schema)
- [Authentication](#authentication)
  - [Create a User / API Token](#create-a-user--api-token)
  - [Default Admin Seed (Dev)](#default-admin-seed-dev)
- [API Overview](#api-overview)
  - [Producer API (Clients)](#producer-api-clients)
  - [Worker API (BYOW)](#worker-api-byow)
  - [Dashboard API](#dashboard-api)
- [End-to-End Example (Enqueue → Lease → Ack)](#end-to-end-example-enqueue--lease--ack)
- [Operational Notes](#operational-notes)
- [Development Notes](#development-notes)
- [Roadmap](#roadmap)
- [License](#license)

---

## Features

- Postgres-backed job storage (JSONB payload/result)
- Job priorities (higher number = higher priority)
- Multi-tenant support via `users` + API tokens
- Worker leasing with a `lease_token`
- `ack` / `nack` semantics
- Basic retries (`retry_count` + `max_retries`)
- Dashboard endpoints for queue stats and job listing
- OpenAPI/Swagger documentation

---

## Concepts

### Job statuses

OpenQueue uses a `status` field (text) with the following common values:

- `pending` — queued and waiting
- `processing` — leased by a worker
- `completed` — successfully finished
- `failed` — failed and no retry scheduled
- `cancelled` — cancelled before processing
- `dead` — reserved for future dead-letter behavior (not fully implemented yet)

### Lease tokens

Workers claim jobs using `lease`. The server returns a `lease_token` which must be provided when acknowledging completion (`ack`) or failure (`nack`).

This prevents:
- two workers from acking the same job
- acking a job you didn’t lease

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

Installed from `requirements.txt` (FastAPI, Uvicorn, asyncpg, etc).

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

> Note: the database schema is initialized automatically on the first boot of the Postgres volume using `schema.sql`.

### Resetting the DB

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
```

Important:
- If your password contains special characters like `@`, you must URL-encode them (e.g. `@` → `%40`).

### 4) Run API

```OpenQueue/README.md#L1-260
uvicorn app.fastapi_app:app --reload
```

---

## Database Schema

Schema is in `schema.sql` and includes:

- `users` — tenants (each API token maps to a user)
- `jobs` — queue items

OpenQueue expects `jobs` to have leasing fields such as:
- `locked_until`, `locked_by`, `lease_token`
- `run_at` for “not before” scheduling
- `started_at`, `finished_at` for timing

---

## Authentication

OpenQueue uses **API tokens**.

- Clients send: `Authorization: Bearer <token>`
- Server computes: `sha256(token)`
- Server checks it against `users.api_token_hash`

Important:
- You **never** store the raw token in Postgres
- You must store the hash (sha256 hex string)

### Create a user / API token

1) Generate a token and hash:

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

### Default admin seed (dev)

If you seed a dev admin in SQL, remember:

- Bearer token must be the **raw token**, not the hash.
- Example:
  - raw token: `oq_admin_dev`
  - stored hash: `sha256("oq_admin_dev")`

Then requests use:

```OpenQueue/README.md#L1-260
Authorization: Bearer oq_admin_dev
```

---

## API Overview

All endpoints are authenticated.

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

Response:

- `{ job_id, status }`

#### `GET /jobs/{job_id}/detail` — Job details

Response:

- full `JobResponse` including payload/result/error and timestamps

#### `GET /jobs` — List jobs

Query:
- `queue_name` (optional)
- `status` (optional)
- `limit` (default 50, max 200)
- `offset` (default 0)

Response:
- `{ items: [...], total, limit, offset }`

#### `POST /jobs/{job_id}/cancel` — Cancel job

Cancels only if job is still `pending`.

---

### Worker API (BYOW)

#### `POST /queues/{queue_name}/lease` — Lease next job

Request body:
- `worker_id` (string)
- `lease_seconds` (int, default 30)

Response:
- `null` if no job available, or:
- `{ job, lease_token, lease_expires_at }`

#### `POST /jobs/{job_id}/ack` — Acknowledge completion

Request body:
- `lease_token` (must match the lease)
- `result` (optional JSON object)

Response:
- `{ job_id, status: "completed" }`

#### `POST /jobs/{job_id}/nack` — Negative acknowledgement

Request body:
- `lease_token`
- `error` (string)
- `retry` (bool, default true)

Behavior:
- If `retry=true` and retries remain: requeues job (`pending`) and increments `retry_count`
- Otherwise: marks job `failed`

Response:
- `{ job_id, status: "failed_or_requeued" }`

---

### Dashboard API

#### `GET /dashboard/queues` — Per-queue statistics

Returns counts by status per queue for the authenticated user.

---

## End-to-End Example (Enqueue → Lease → Ack)

### 1) Enqueue

```OpenQueue/README.md#L1-260
curl -X POST "http://127.0.0.1:8000/jobs" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "queue_name": "default",
    "payload": {"task": "demo", "n": 1},
    "priority": 10,
    "max_retries": 3
  }'
```

### 2) Lease (worker)

```OpenQueue/README.md#L1-260
curl -X POST "http://127.0.0.1:8000/queues/default/lease" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"worker_id":"worker-1","lease_seconds":30}'
```

Copy `job.id` and `lease_token` from the response.

### 3) Ack (worker)

```OpenQueue/README.md#L1-260
curl -X POST "http://127.0.0.1:8000/jobs/<JOB_ID>/ack" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"lease_token":"<LEASE_TOKEN>","result":{"ok":true}}'
```

---

## Operational Notes

- **At-least-once processing**: Workers should be idempotent.
- **Lease expiry recovery**: current implementation includes lease fields, but timed-out job recovery/re-leasing policies can be expanded.
- **Retries**: basic requeue exists; backoff/delay can be added via `run_at`.

---

## Development Notes

- Run formatting/linting as you prefer (not included yet).
- Prefer adding schema changes via migrations (Alembic) in future iterations.

---

## Roadmap

High-priority next steps:

- Visibility timeout requeue (auto-detect expired leases)
- Backoff strategy + delayed retries (`run_at`)
- Dead-letter queue behavior (`dead`)
- Admin endpoints / dashboard UI for managing users + tokens
- Rate limiting and quotas per tenant
- Metrics (Prometheus) + tracing

---

## License

See `LICENSE`.