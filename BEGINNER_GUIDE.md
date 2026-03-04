## OpenQueue Beginner Guide

This guide is for a **junior engineer who wants to become “pro‑level”** at understanding how this project works end‑to‑end.

It explains:

- **What technologies are used** (FastAPI, Starlette/ASGI, PostgreSQL, asyncpg, Prometheus, Alembic, pytest, etc.)
- **How HTTP requests flow through the app**
- **How jobs move through the queue** (enqueue → lease → ack/nack → DLQ)
- **Where to look in the codebase** when you are debugging or extending features

You can read this file top‑to‑bottom once, then treat it as a reference.

---

### 1. Big picture: what OpenQueue is

- **OpenQueue** is a **hosted job queue service**.
  - Producers send HTTP requests to **enqueue jobs**.
  - Workers send HTTP requests to **lease jobs, process them, and ack/nack results**.
  - All jobs are stored in **PostgreSQL**, not in memory.
- The service is implemented as a **FastAPI application** running on an **ASGI server** (like `uvicorn`) and uses:
  - **Starlette** (the low‑level web framework FastAPI sits on)
  - **async/await** for concurrency
  - **asyncpg** for asynchronous Postgres access
  - **Prometheus** metrics and health endpoints for observability
  - **Alembic** for database migrations

Mentally, imagine three boxes:

- **Clients** (your apps + your workers) → send HTTP requests.
- **FastAPI service** (this repo) → authenticates, validates, applies business rules, talks to DB.
- **PostgreSQL** → actual storage and queue logic via SQL + row locking.

---

### 2. The Python web stack: ASGI → Starlette → FastAPI

#### 2.1 ASGI (the foundation)

- **ASGI** = Asynchronous Server Gateway Interface.
  - It is a **standard** that defines how async Python web servers (like `uvicorn`) talk to Python applications.
  - An ASGI app is basically a **callable** that the server calls for every request.
- Why it matters here:
  - Because ASGI is **async**, you can use `async def` endpoints and non‑blocking DB drivers like `asyncpg`.
  - Middleware, lifespan events, and WebSockets all build on top of ASGI.

You generally don’t write pure ASGI in this project – **FastAPI and Starlette hide the low‑level details**, but they are built on top of it.

#### 2.2 Starlette (the lower‑level framework)

- **Starlette** is a lightweight ASGI framework:
  - Routing
  - Middleware
  - Request/response objects
  - Background tasks, WebSockets, etc.
- In this project, you see **Starlette concepts** mainly in:
  - `Request` / `Response` objects
  - `BaseHTTPMiddleware` for custom middleware (logging, metrics, request IDs)

You don’t normally import Starlette directly; instead, FastAPI re‑exports many of the pieces.

#### 2.3 FastAPI (the high‑level framework)

- **FastAPI** sits on top of Starlette and adds:
  - Super convenient **routing** with decorators like `@router.get`, `@router.post`.
  - **Dependency injection** (the `Depends(...)` system).
  - **Request body parsing** and **response models** via Pydantic.
  - Automatic **OpenAPI schema** and interactive docs (`/docs`).
- In this project, the main FastAPI setup is:
  - `app/fastapi_app.py` → exposes the `app` object for `uvicorn`.
  - `app/core/app_factory.py` → builds and configures the FastAPI app:
    - sets metadata (title, version, description)
    - registers **middleware**
    - includes **routers**.

The important mental model:

- **FastAPI = high‑level framework for HTTP APIs.**
  - You think in terms of **endpoints, request models, response models, and dependencies**.

---

### 3. Pydantic: data validation and models

- **Pydantic** is used to define **request and response schemas**.
  - You define models as Python classes with type hints.
  - Pydantic automatically validates and converts incoming JSON into those models.
- In this project:
  - `app/models.py` contains:
    - `JobCreate` – request body for `POST /jobs`.
    - `JobResponse` – response structure when returning job data.
    - `LeaseRequest`, `LeaseResponse`, `AckRequest`, `NackRequest`, `HeartbeatRequest` – request/response models for worker APIs.
    - `JobListResponse` – paginated list for dashboards.

By using Pydantic:

- Endpoints get **typed, validated Python objects** instead of raw dicts.
- OpenAPI docs are generated automatically from these models.

---

### 4. Request lifecycle in this project

This is **the key mental model** that will make you feel “pro” when reading the code.

We’ll follow a **typical request**, for example `POST /jobs` (enqueue a job).

#### 4.1 Step 1 – HTTP request hits the ASGI server

- `uvicorn` receives an HTTP request from a client.
- It passes it to the ASGI app exposed in:
  - `app/fastapi_app.py` → `app = create_app(...)`.
  - `create_app` is defined in `app/core/app_factory.py`.

#### 4.2 Step 2 – Middleware runs

In `create_app`, middleware is registered:

- **RequestIdMiddleware** (`app/middleware.py`)
  - Ensures every request has a unique `X-Request-ID`.
  - Stores it on `request.state.request_id`.
- **StructuredLoggingMiddleware**
  - Logs a **single structured line** per request (method, path, status, duration, client IP, user agent, request ID).
- **PrometheusHttpMetricsMiddleware**
  - Updates Prometheus counters/histograms:
    - total HTTP requests
    - request duration by method/path.

Conceptually:

- Middleware **wraps** the request handling.
- They run **before and after** your endpoint handler.

#### 4.3 Step 3 – Routing & dependency injection

- FastAPI matches the request to the appropriate **router & endpoint function**:
  - Producers: `app/routers/jobs.py`
  - Workers: `app/routers/workers.py`
  - Dashboard: `app/routers/dashboard.py`
  - Observability: `app/routers/observability.py`
- Each endpoint **declares dependencies** using `Depends(...)`, for example:
  - `AuthUserDep` – resolves the current user from the `Authorization: Bearer <token>` header using `app/auth.py`.
  - Rate‑limit dependencies – e.g. `RateLimitEnqueueDep` using `app/deps.py` and `app/rate_limit.py`.

FastAPI automatically:

- Parses the request body into a Pydantic model.
- Resolves dependencies (auth, rate limits, etc.).
- Calls your endpoint function with **already validated** arguments.

#### 4.4 Step 4 – Service layer (business logic)

Endpoints in routers are **kept intentionally thin**:

- They import functions from `app/services/jobs_service.py`, such as:
  - `enqueue_job`
  - `lease_next`
  - `ack`
  - `nack`
  - `heartbeat`
  - `list_user_jobs`
  - `queue_stats`.

The service layer is where you see:

- **Business rules** (e.g. metrics labels, return shaping).
- **Prometheus metrics** for operations (enqueued, leased, acked, nacked, DLQ moves, etc.).
- Simple transformations of data from the DB layer into Pydantic models.

This separation gives you a **clean mental map**:

- Router = **HTTP surface + auth + rate limits**.
- Service = **business rules + metrics**.
- CRUD = **SQL and DB details**.

#### 4.5 Step 5 – CRUD layer & database access

- `app/crud.py` is where **real SQL lives**:
  - Insert jobs (`create_job`).
  - Select jobs (`get_job_status`, `get_job`, `list_jobs`).
  - Lease jobs (`lease_next_job`) with **row locking**.
  - Update on ack/nack/heartbeat/cancel (`ack_job`, `nack_job`, `heartbeat_job`, `cancel_job`).
  - Queue stats (`get_queue_stats`).
- The CRUD layer talks to Postgres via a **connection pool** provided by:
  - `app/database.py` → a `Database` class that wraps an `asyncpg.Pool`.

When a CRUD function is called:

- It uses `async with db.get_pool() as pool:`
  - Then `async with pool.acquire() as conn:` to get a connection.
  - Then executes SQL with `conn.fetch`, `conn.fetchrow`, `conn.execute`, etc.

Because all of this is **async**, multiple requests can share the connection pool efficiently.

#### 4.6 Step 6 – Response building

- CRUD returns raw data (e.g. dicts or `asyncpg.Record` objects).
- Service functions convert them into **plain dicts or Pydantic models**.
- Routers return Pydantic models (or dicts) and FastAPI turns them into JSON responses.
- Middleware wraps the response:
  - logging
  - metrics
  - request ID headers.

From the outside, clients just see:

- A clean JSON API with documented responses.

---

### 5. Database & SQL in this project

#### 5.1 PostgreSQL as the queue engine

- OpenQueue uses **PostgreSQL** as both:
  - a **data store** (`users`, `jobs` tables),
  - a **queue engine** using **row locks**.
- Key ideas:
  - Jobs are rows in a `jobs` table.
  - Leasing uses:
    - `SELECT ... FOR UPDATE SKIP LOCKED` to **atomically claim a job**.
    - `locked_until`, `locked_by`, `lease_token` columns to track leases.
  - Retry and delayed execution use:
    - `run_at` (a timestamp field).

Because everything is in Postgres:

- You get **durability** and can debug with SQL queries.

#### 5.2 asyncpg: async driver for Postgres

- **asyncpg** is an **asynchronous Postgres driver**.
  - It exposes an `asyncpg.Pool` for connection pooling.
  - Queries are `await`‑ed: `await conn.fetch(...)`, `await conn.execute(...)`.
- In `app/database.py`:
  - `Database._ensure_pool` creates a pool lazily using the URL from settings.
  - `get_pool` is an async context manager that yields the pool.

Why async matters:

- While one request is waiting on IO (DB call), the event loop can handle another request.
- This allows a single process to handle many concurrent requests efficiently.

#### 5.3 Alembic: migrations

- **Alembic** is used to manage DB schema changes over time.
  - Migration scripts live under `migrations/`.
  - `alembic upgrade head` brings your DB up to the latest schema.
- The CI workflow:
  - Starts Postgres.
  - Runs `alembic upgrade head`.
  - Then runs `pytest`.

This ensures:

- Your schema and code stay in sync in all environments.

---

### 6. Authentication & security model

#### 6.1 API tokens

- Authentication is **API‑token based**:
  - Clients send `Authorization: Bearer <token>`.
  - The app hashes the token and looks up a user row in the `users` table.
- Token hashing is done in `app/auth.py`:
  - By default: `sha256(token)`.
  - If `OPENQUEUE_TOKEN_HMAC_SECRET` is set, then: `HMAC-SHA256(secret, token)`.
- Why HMAC?
  - If the DB leaks, an attacker **cannot easily guess valid tokens** without the secret.

#### 6.2 FastAPI security dependency

- FastAPI’s `HTTPBearer` security scheme parses the `Authorization` header.
- `get_current_user`:
  - extracts the token,
  - hashes it,
  - looks up the user in DB,
  - ensures `is_active` is true,
  - updates `last_seen_at`.
- Routers use `AuthUserDep` from `app/deps.py` so every authenticated endpoint **automatically** has the current user.

Mentally:

- “Current user” is always available as a dict (`{"id": ..., "email": ..., "is_active": ...}`) to endpoint and service code.

---

### 7. Rate limiting & payload guardrails

#### 7.1 In‑memory token‑bucket rate limiting

- `app/rate_limit.py` defines:
  - `RateLimit` – a rate + burst (tokens/sec, bucket size).
  - `RateLimiter` – a token‑bucket implementation keyed by **(principal, action)**.
  - `DEFAULT_LIMITS` – per‑action defaults:
    - `enqueue`, `lease`, `ack`, `nack`, `heartbeat`, `list_jobs`, `queue_stats`.
- `app/deps.py` wires this into FastAPI dependencies:
  - `RateLimitEnqueueDep`, `RateLimitLeaseDep`, etc.
- Each request:
  - Computes a **principal key** (usually the user id).
  - Consumes tokens from the appropriate bucket.
  - Raises a `429 Too Many Requests` if the bucket is empty, with a `Retry-After` header.

This protects:

- The API from abusive or buggy clients.
- The database from being flooded with operations.

#### 7.2 Payload size limits

- `app/rate_limit.py` also provides:
  - `enforce_json_size_guardrail` – checks raw request body length against a limit.
- `app/settings.py` defines:
  - `max_enqueue_payload_bytes`
  - `max_result_payload_bytes`
  - `max_error_text_bytes`.

These settings let you control **how big requests and results can be**.

---

### 8. Job lifecycle: from enqueue to DLQ

Understanding this makes the whole system “click”.

#### 8.1 Enqueue (`POST /jobs`)

1. Client calls `POST /jobs` with `JobCreate` payload.
2. Auth + rate limiting run.
3. `jobs_service.enqueue_job` is called.
4. `crud.create_job` inserts a row into `jobs`:
   - `status = 'pending'`
   - `run_at = NOW()` by default
   - `retry_count = 0`, `max_retries` from request
   - `priority` from request.
5. Metrics counter `JOBS_ENQUEUED_TOTAL` is incremented.

Result: **job row appears in DB** and is now leaseable.

#### 8.2 Lease (`POST /queues/{queue_name}/lease`)

1. Worker sends a `LeaseRequest` (worker id, lease seconds).
2. Auth + rate limiting run.
3. `jobs_service.lease_next` calls `crud.lease_next_job`.
4. `lease_next_job`:
   - Finds **one qualifying job**:
     - `status = 'pending' AND run_at <= NOW()` or
     - `status = 'processing' AND locked_until < NOW()` (expired lease).
   - Orders by:
     - `priority DESC`
     - `created_at ASC` (FIFO inside priority).
   - Uses `FOR UPDATE SKIP LOCKED` to avoid race conditions.
   - Updates:
     - `status = 'processing'`
     - `locked_by = worker_id`
     - `locked_until = NOW() + lease_seconds`
     - `lease_token = gen_random_uuid()`
     - `lease_lost_count` if it was expired.
5. `LeaseResult` is returned and then exposed as a `LeaseResponse` to the worker.

If there is no job, the endpoint returns `null`.

#### 8.3 Ack (`POST /jobs/{job_id}/ack`)

1. Worker sends `AckRequest` with the `lease_token` and optional result JSON.
2. Auth + rate limiting run.
3. `jobs_service.ack` calls `crud.ack_job`.
4. `ack_job` updates the row only if:
   - `id`, `user_id`, `status = 'processing'`, and `lease_token` all match.
5. If the update succeeds:
   - `status = 'completed'`
   - `result` is stored
   - `finished_at` is set
   - lease metadata is cleared.
6. Metrics: `JOBS_ACKED_TOTAL` is incremented.

If anything doesn’t match (wrong token, wrong status, wrong user), the endpoint returns `409 Conflict`.

#### 8.4 Nack (`POST /jobs/{job_id}/nack`)

1. Worker sends `NackRequest` with `lease_token`, `error` string, `retry` bool.
2. Auth + rate limiting run.
3. `jobs_service.nack` calls `crud.nack_job`.
4. `nack_job`:
   - Checks that the job is `processing` and the `lease_token` matches.
   - Reads `retry_count` and `max_retries`.
   - If `retry=True` and retries remain:
     - `status = 'pending'`
     - `retry_count += 1`
     - `run_at = NOW() + backoff_seconds` (exponential backoff)
     - lease metadata is cleared.
   - Else (no retries left or `retry=False`):
     - `status = 'dead'`
     - `dead_reason` and `dead_at` set
     - `error_text` updated
     - `finished_at` set.
5. Metrics:
   - `JOBS_NACKED_TOTAL` increments.
   - `JOBS_MOVED_TO_DLQ_TOTAL` increments in some cases.

Result: job is either **requeued for later** or **sent to the DLQ**.

#### 8.5 Heartbeat (`POST /jobs/{job_id}/heartbeat`)

1. Worker sends `HeartbeatRequest` (lease token, new lease seconds).
2. Auth + rate limiting run.
3. `jobs_service.heartbeat` calls `crud.heartbeat_job`.
4. `heartbeat_job`:
   - Updates `locked_until = NOW() + lease_seconds`
   - Only if `status = 'processing'` and `lease_token` matches.

This keeps long‑running jobs from being re‑leased to another worker.

---

### 9. Observability & maintenance

#### 9.1 Observability

- **Metrics**:
  - Defined in `app/metrics.py`.
  - Exposed at `/metrics` via `app/routers/observability.py`.
  - Include:
    - HTTP request counts & latencies.
    - Jobs enqueued, leased, acked, nacked, cancelled, DLQ’d.
    - Lease expiry recoveries.
    - Processing duration histograms.
- **Health checks**:
  - `/health` – liveness (process is up).
  - `/ready` – readiness (can connect to DB and run `SELECT 1`).

These are what you’d hook up to **Kubernetes, monitoring, dashboards, and alerts**.

#### 9.2 Maintenance

- `app/maintenance.py` defines:
  - `reap_expired_leases` – policy hook to clean up jobs stuck in `processing`.
  - `delete_old_jobs` – delete jobs of certain statuses older than a TTL.
  - `run_maintenance_once` – run one iteration of all tasks.
  - `maintenance_loop` – long‑running async loop to run maintenance periodically.
- In production, you typically:
  - Run maintenance in a **separate worker process or container**.
  - Configure intervals and retention with `MaintenanceConfig`.

---

### 10. Testing & CI

#### 10.1 pytest & pytest‑asyncio

- `pyproject.toml` configures pytest:
  - Async tests with `pytest-asyncio`.
  - Test paths in `tests/`.
- A key test is `tests/test_concurrency_leasing.py`:
  - Boots a minimal schema (or uses your migrations).
  - Enqueues 100 jobs.
  - Uses many concurrent “workers” to lease jobs.
  - Asserts that:
    - There are **no duplicate leases**.
    - All jobs end up leased exactly once.

This gives strong evidence that the **leasing algorithm is correct under concurrency**.

#### 10.2 GitHub Actions CI

- `.github/workflows/test.yml`:
  - Starts Postgres as a service.
  - Sets `DATABASE_URL` and `OPENQUEUE_TOKEN_HMAC_SECRET`.
  - Installs dependencies.
  - Runs Alembic migrations.
  - Runs pytest.

When CI is green, you know:

- DB schema + migrations + code + tests **all agree**.

---

### 11. How to continue leveling up

To go from “understands the guide” to “pro at this codebase”, here’s a suggested path:

- **Step 1 – Trace one happy path end‑to‑end**
  - Start at `POST /jobs` in `app/routers/jobs.py`.
  - Follow calls through `services.jobs_service`, then `crud`, then skim the SQL.
  - Check the `jobs` table definition in migrations.
- **Step 2 – Trace one worker path**
  - `POST /queues/{queue_name}/lease` → lease job.
  - `POST /jobs/{job_id}/ack` → complete job.
  - `POST /jobs/{job_id}/nack` → DLQ behavior.
- **Step 3 – Explore cross‑cutting concerns**
  - Read `app/auth.py` and `app/deps.py` to fully grok auth and rate limiting.
  - Read `app/middleware.py` + `app/metrics.py` to understand logging/metrics.
- **Step 4 – Run and observe**
  - Run the app locally.
  - Use the `/docs` UI to enqueue and lease jobs.
  - Watch logs and `/metrics` output to see it all in action.

After you can comfortably navigate those flows without re‑opening this guide, you’ve effectively **“mastered” the architecture and core concepts** of this project.

