from __future__ import annotations

from typing import Annotated, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field

from .auth import CurrentUser, get_current_user
from .crud import (
    ack_job,
    cancel_job,
    create_job,
    get_job,
    get_job_status,
    get_queue_stats,
    heartbeat_job,
    lease_next_job,
    list_jobs,
    nack_job,
)
from .metrics import (
    JOBS_ACKED_TOTAL,
    JOBS_CANCELLED_TOTAL,
    JOBS_ENQUEUED_TOTAL,
    JOBS_LEASE_EMPTY_TOTAL,
    JOBS_LEASED_TOTAL,
    JOBS_MOVED_TO_DLQ_TOTAL,
    JOBS_NACKED_TOTAL,
    LEASE_EXPIRED_RECOVERED_TOTAL,
)
from .middleware import (
    PrometheusHttpMetricsMiddleware,
    RequestIdMiddleware,
    StructuredLoggingMiddleware,
)
from .models import (
    AckRequest,
    JobCreate,
    JobListResponse,
    JobResponse,
    LeaseRequest,
    LeaseResponse,
    NackRequest,
)
from .rate_limit import DEFAULT_LIMITS, RateLimiter, RateLimitExceeded

# -------------------------
# OpenAPI / Docs Models
# -------------------------


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Human-readable error message")


class EnqueueJobResponse(BaseModel):
    job_id: str = Field(..., description="Enqueued job id (UUID as string)")
    status: Literal["queued"] = Field("queued", description="Enqueue status")


class JobStatusResponse(BaseModel):
    job_id: str = Field(..., description="Job id (UUID as string)")
    status: str = Field(..., description="Current job status")


class CancelJobResponse(BaseModel):
    job_id: str = Field(..., description="Job id (UUID as string)")
    status: Literal["cancelled"] = Field("cancelled", description="Cancellation status")


class AckJobResponse(BaseModel):
    job_id: str = Field(..., description="Job id (UUID as string)")
    status: Literal["completed"] = Field("completed", description="Completion status")


class NackJobResponse(BaseModel):
    job_id: str = Field(..., description="Job id (UUID as string)")
    status: Literal["failed_or_requeued"] = Field(
        "failed_or_requeued",
        description="Outcome after negative acknowledgement (failed or requeued)",
    )


class HeartbeatRequest(BaseModel):
    lease_token: str = Field(
        ..., description="Lease token returned by the lease endpoint"
    )
    lease_seconds: int = Field(
        default=30,
        ge=1,
        le=3600,
        description="New lease duration (seconds) starting from now",
    )


class HeartbeatResponse(BaseModel):
    job_id: str = Field(..., description="Job id (UUID as string)")
    status: Literal["lease_extended"] = Field(
        "lease_extended", description="Lease was successfully extended"
    )


class QueueStatsItem(BaseModel):
    queue_name: str
    pending: int
    processing: int
    completed: int
    failed: int
    cancelled: int | None = None
    dead: int | None = None
    total: int
    oldest_pending_created_at: Optional[str] = None


# -------------------------
# App
# -------------------------

tags_metadata = [
    {
        "name": "Jobs (Producer)",
        "description": "Client-facing endpoints to enqueue jobs and inspect/cancel them.",
    },
    {
        "name": "Workers (BYOW)",
        "description": "Worker endpoints to lease jobs and ack/nack/heartbeat results. BYOW = Bring Your Own Worker.",
    },
    {
        "name": "Dashboard",
        "description": "Read-only endpoints for queue statistics and listings.",
    },
    {
        "name": "Observability",
        "description": "Operational endpoints such as Prometheus metrics.",
    },
]

app = FastAPI(
    title="OpenQueue",
    version="0.0.1",
    summary="Hosted, Postgres-backed job queue service",
    description=(
        "OpenQueue is a hosted queue service intended to replace Redis queues for many workloads. "
        "Clients enqueue jobs, and workers lease jobs for processing using a lease token.\n\n"
        "## Authentication\n"
        "All endpoints require an API token via `Authorization: Bearer <token>`.\n\n"
        "## Worker semantics\n"
        "- `lease`: atomically claims the next eligible job in a queue.\n"
        "- `ack`: completes a leased job.\n"
        "- `nack`: fails a leased job, optionally requeueing if retries remain.\n"
        "- `heartbeat`: extends a lease for long-running jobs.\n"
    ),
    openapi_tags=tags_metadata,
)

# Middleware: request id, structured logs, and Prometheus HTTP metrics
app.add_middleware(RequestIdMiddleware)
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(PrometheusHttpMetricsMiddleware)

# In-memory rate limiter (per-process). For multi-replica deployments, replace with distributed limiter.
rate_limiter = RateLimiter(default_limits=DEFAULT_LIMITS)

AuthUserDep = Annotated[CurrentUser, Depends(get_current_user)]

# Common OpenAPI responses to improve Postman visibility
RESP_401 = {
    "model": ErrorResponse,
    "description": "Unauthorized (missing/invalid token)",
}
RESP_403 = {"model": ErrorResponse, "description": "Forbidden (inactive user)"}
RESP_404 = {"model": ErrorResponse, "description": "Not found"}
RESP_409 = {
    "model": ErrorResponse,
    "description": "Conflict (lease mismatch / invalid state)",
}
RESP_500 = {"model": ErrorResponse, "description": "Internal server error"}


@app.get(
    "/health",
    tags=["Dashboard"],
    summary="Health check (liveness)",
    description="Liveness probe. Returns OK if the HTTP process is running.",
    response_model=dict,
)
async def health() -> dict:
    return {"status": "ok"}


@app.get(
    "/metrics",
    tags=["Observability"],
    summary="Prometheus metrics",
    description="Expose Prometheus metrics for OpenQueue.",
    response_class=Response,
)
async def metrics() -> Response:
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@app.get(
    "/ready",
    tags=["Dashboard"],
    summary="Readiness check (DB connectivity)",
    description="Readiness probe. Returns OK only if the service can reach the database.",
    response_model=dict,
    responses={500: RESP_500},
)
async def ready(user: AuthUserDep) -> dict:
    # We currently validate DB connectivity via the auth dependency, since it performs a DB lookup.
    # If you later want readiness without auth, add a DB ping query in CRUD and call it here.
    return {"status": "ready"}


# -------------------------
# Producer API (Clients)
# -------------------------


@app.post(
    "/jobs",
    tags=["Jobs (Producer)"],
    summary="Enqueue a job",
    description="Create a new job in a named queue.",
    response_model=EnqueueJobResponse,
    status_code=status.HTTP_201_CREATED,
    responses={401: RESP_401, 403: RESP_403},
)
async def job_create(
    job: JobCreate, user: AuthUserDep, request: Request
) -> EnqueueJobResponse:
    # Rate limit: enqueue
    principal = getattr(
        request.state, "request_id", None
    )  # fallback if auth changes; not ideal
    # Prefer token hash principal if available in auth later; for now use user_id to avoid raw token usage.
    principal = user["id"] if user and user.get("id") else (principal or "unknown")
    try:
        rate_limiter.consume(principal_key=principal, action="enqueue")
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(int(max(1.0, e.retry_after_seconds)))},
        )

    job_id = await create_job(
        user_id=user["id"],
        queue_name=job.queue_name,
        payload=job.payload,
        priority=job.priority,
        max_retries=job.max_retries,
    )

    JOBS_ENQUEUED_TOTAL.labels(queue_name=job.queue_name).inc()
    return EnqueueJobResponse(job_id=str(job_id), status="queued")


@app.get(
    "/jobs/{job_id}",
    tags=["Jobs (Producer)"],
    summary="Get job status",
    description="Return only the job status for a job belonging to the authenticated user.",
    response_model=JobStatusResponse,
    responses={401: RESP_401, 403: RESP_403, 404: RESP_404},
)
async def job_status(job_id: str, user: AuthUserDep) -> JobStatusResponse:
    status_value = await get_job_status(user_id=user["id"], job_id=job_id)
    if not status_value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return JobStatusResponse(job_id=job_id, status=status_value)


@app.get(
    "/jobs/{job_id}/detail",
    tags=["Jobs (Producer)"],
    summary="Get job details",
    description="Return full job details (payload/result/error and timestamps).",
    response_model=JobResponse,
    responses={401: RESP_401, 403: RESP_403, 404: RESP_404},
)
async def job_get(job_id: str, user: AuthUserDep) -> JobResponse:
    job = await get_job(user_id=user["id"], job_id=job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return job  # type: ignore[return-value]


@app.get(
    "/jobs",
    tags=["Jobs (Producer)"],
    summary="List jobs",
    description=(
        "List jobs for the authenticated user.\n\n"
        "Use filters for dashboards and operational views."
    ),
    response_model=JobListResponse,
    responses={401: RESP_401, 403: RESP_403},
)
async def jobs_list(
    user: AuthUserDep,
    request: Request,
    queue_name: Optional[str] = Query(default=None, description="Filter by queue name"),
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter by job status (e.g. pending, processing, completed, failed)",
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Max items to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
) -> JobListResponse:
    # Rate limit: list jobs
    principal = user["id"]
    try:
        rate_limiter.consume(principal_key=principal, action="list_jobs")
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(int(max(1.0, e.retry_after_seconds)))},
        )

    items, total = await list_jobs(
        user_id=user["id"],
        queue_name=queue_name,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return JobListResponse(
        items=[JobResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.post(
    "/jobs/{job_id}/cancel",
    tags=["Jobs (Producer)"],
    summary="Cancel a pending job",
    description="Cancels a job only if it is still pending.",
    response_model=CancelJobResponse,
    responses={401: RESP_401, 403: RESP_403, 404: RESP_404},
)
async def job_cancel(job_id: str, user: AuthUserDep) -> CancelJobResponse:
    ok = await cancel_job(user_id=user["id"], job_id=job_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or not cancellable",
        )
    JOBS_CANCELLED_TOTAL.labels(queue_name="unknown").inc()
    return CancelJobResponse(job_id=job_id, status="cancelled")


# -------------------------
# Worker API (BYOW)
# -------------------------


@app.post(
    "/queues/{queue_name}/lease",
    tags=["Workers (BYOW)"],
    summary="Lease next job in queue",
    description=(
        "Atomically claim the next available job in a queue and return it with a lease token.\n\n"
        "If no job is available, returns `null`.\n\n"
        "The lease token must be used for `ack`/`nack`/`heartbeat`."
    ),
    response_model=Optional[LeaseResponse],
    responses={401: RESP_401, 403: RESP_403, 500: RESP_500},
)
async def queue_lease(
    queue_name: str,
    req: LeaseRequest,
    user: AuthUserDep,
    request: Request,
) -> Optional[LeaseResponse]:
    # Rate limit: lease
    principal = user["id"]
    try:
        rate_limiter.consume(principal_key=principal, action="lease")
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(int(max(1.0, e.retry_after_seconds)))},
        )

    leased = await lease_next_job(
        user_id=user["id"],
        queue_name=queue_name,
        worker_id=req.worker_id,
        lease_seconds=req.lease_seconds,
    )
    if not leased:
        JOBS_LEASE_EMPTY_TOTAL.labels(queue_name=queue_name).inc()
        return None

    lease_token = leased.get("lease_token")
    lease_expires_at = leased.get("locked_until")
    if not lease_token or not lease_expires_at:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lease created but missing lease metadata",
        )

    job_dict = dict(leased)
    job_dict.pop("lease_token", None)
    job_dict.pop("locked_until", None)

    # Best-effort: record recovery metric if lease_lost_count increased (requires that field present)
    if leased.get("lease_lost_count"):
        LEASE_EXPIRED_RECOVERED_TOTAL.labels(queue_name=queue_name).inc()

    JOBS_LEASED_TOTAL.labels(queue_name=queue_name).inc()
    return LeaseResponse(
        job=job_dict,  # type: ignore[arg-type]
        lease_token=str(lease_token),
        lease_expires_at=str(lease_expires_at),
    )


@app.post(
    "/jobs/{job_id}/ack",
    tags=["Workers (BYOW)"],
    summary="Acknowledge job completion",
    description="Completes a leased job. Requires the lease token returned by `lease`.",
    response_model=AckJobResponse,
    responses={401: RESP_401, 403: RESP_403, 409: RESP_409},
)
async def job_ack(
    job_id: str, req: AckRequest, user: AuthUserDep, request: Request
) -> AckJobResponse:
    # Rate limit: ack
    principal = user["id"]
    try:
        rate_limiter.consume(principal_key=principal, action="ack")
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(int(max(1.0, e.retry_after_seconds)))},
        )

    ok = await ack_job(
        user_id=user["id"],
        job_id=job_id,
        lease_token=req.lease_token,
        result=req.result,
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job not found, not leased, or lease token mismatch",
        )
    JOBS_ACKED_TOTAL.labels(queue_name="unknown").inc()
    return AckJobResponse(job_id=job_id, status="completed")


@app.post(
    "/jobs/{job_id}/nack",
    tags=["Workers (BYOW)"],
    summary="Negative-acknowledge a job",
    description=(
        "Marks a leased job as failed. If `retry=true` and retries remain, the job is requeued "
        "using exponential backoff via `run_at`. If retries are exhausted (or retry is disabled), "
        "the job is moved to the DLQ (`dead`).\n\n"
        "This endpoint is used when a worker fails to process a job."
    ),
    response_model=NackJobResponse,
    responses={401: RESP_401, 403: RESP_403, 409: RESP_409},
)
async def job_nack(
    job_id: str, req: NackRequest, user: AuthUserDep, request: Request
) -> NackJobResponse:
    # Rate limit: nack
    principal = user["id"]
    try:
        rate_limiter.consume(principal_key=principal, action="nack")
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(int(max(1.0, e.retry_after_seconds)))},
        )

    ok = await nack_job(
        user_id=user["id"],
        job_id=job_id,
        lease_token=req.lease_token,
        error=req.error,
        retry=req.retry,
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job not found, not leased, or lease token mismatch",
        )

    # We can't perfectly know outcome without reading job state back; record generic nack.
    JOBS_NACKED_TOTAL.labels(queue_name="unknown", outcome="nack").inc()
    # DLQ moves are counted inside CRUD in a future enhancement; keep metric placeholder here.
    if not req.retry:
        JOBS_MOVED_TO_DLQ_TOTAL.labels(
            queue_name="unknown", reason="retry_disabled"
        ).inc()

    return NackJobResponse(job_id=job_id, status="failed_or_requeued")


@app.post(
    "/jobs/{job_id}/heartbeat",
    tags=["Workers (BYOW)"],
    summary="Extend a job lease (heartbeat)",
    description=(
        "Extends the lease for a long-running job. Requires the current `lease_token`.\n\n"
        "Use this periodically for jobs that take longer than the original lease duration."
    ),
    response_model=HeartbeatResponse,
    responses={401: RESP_401, 403: RESP_403, 409: RESP_409},
)
async def job_heartbeat(
    job_id: str, req: HeartbeatRequest, user: AuthUserDep, request: Request
) -> HeartbeatResponse:
    # Rate limit: heartbeat
    principal = user["id"]
    try:
        rate_limiter.consume(principal_key=principal, action="heartbeat")
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(int(max(1.0, e.retry_after_seconds)))},
        )

    ok = await heartbeat_job(
        user_id=user["id"],
        job_id=job_id,
        lease_token=req.lease_token,
        lease_seconds=req.lease_seconds,
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job not found, not leased, or lease token mismatch",
        )
    return HeartbeatResponse(job_id=job_id, status="lease_extended")


# -------------------------
# Dashboard API (Stats)
# -------------------------


@app.get(
    "/dashboard/queues",
    tags=["Dashboard"],
    summary="Queue statistics",
    description="Returns per-queue counts by status for the authenticated user.",
    response_model=list[QueueStatsItem],
    responses={401: RESP_401, 403: RESP_403},
)
async def dashboard_queues(user: AuthUserDep, request: Request) -> list[QueueStatsItem]:
    # Rate limit: queue stats
    principal = user["id"]
    try:
        rate_limiter.consume(principal_key=principal, action="queue_stats")
    except RateLimitExceeded as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(int(max(1.0, e.retry_after_seconds)))},
        )

    stats = await get_queue_stats(user_id=user["id"])
    return stats  # type: ignore[return-value]
