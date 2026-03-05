from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .. import crud
from ..metrics import (
    JOBS_ACKED_TOTAL,
    JOBS_CANCELLED_TOTAL,
    JOBS_ENQUEUED_TOTAL,
    JOBS_LEASE_EMPTY_TOTAL,
    JOBS_LEASED_TOTAL,
    JOBS_MOVED_TO_DLQ_TOTAL,
    JOBS_NACKED_TOTAL,
    LEASE_EXPIRED_RECOVERED_TOTAL,
)
from ..models import JobCreate

"""
Jobs service layer.

Purpose
-------
This module centralizes business rules and cross-cutting concerns around job and
worker operations (enqueue/lease/ack/nack/heartbeat/cancel/listing).

Design goals:
- Keep endpoints thin (routers call service functions).
- Keep CRUD focused on raw SQL and DB interaction.
- Keep cross-cutting concerns centralized:
  - Prometheus metrics increments
  - Small business rules / normalization
  - Optional post-processing of returned job dicts

Non-goals:
- This is NOT an ORM layer.
- This does not attempt to hide SQL semantics; the queue "hot path" stays in CRUD.

Notes:
- We avoid high-cardinality metric labels (never label by job_id/lease_token/user).
- queue_name may still be high-cardinality in some deployments. Use carefully.
"""


@dataclass(frozen=True)
class LeaseResult:
    """
    Represents the lease response returned to a worker.

    - job: the job record (without sensitive lease fields)
    - lease_token: token required for ack/nack/heartbeat
    - lease_expires_at: ISO timestamp string
    """

    job: Dict[str, Any]
    lease_token: str
    lease_expires_at: str


def _safe_queue_label(queue_name: Optional[str]) -> str:
    """
    Metrics label helper.

    Avoid exploding label cardinality. For now, we label by queue_name for
    producer/worker operations because it can be valuable. If queues are unbounded
    in your hosted offering, replace this with a small set of buckets or "unknown".
    """
    return (queue_name or "unknown").strip() or "unknown"


def _parse_lease_fields(leased_job: Dict[str, Any]) -> Tuple[str, str]:
    """
    Extract lease_token and lease expiry from the leased job dict.

    CRUD returns a dict that includes:
    - lease_token
    - locked_until
    """
    lease_token = leased_job.get("lease_token")
    lease_expires_at = leased_job.get("locked_until")

    if not lease_token or not lease_expires_at:
        raise RuntimeError("Lease created but missing lease metadata")

    return str(lease_token), str(lease_expires_at)


def _strip_lease_fields(job_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove lease-only fields from the job dict returned to workers.
    """
    job = dict(job_dict)
    job.pop("lease_token", None)
    job.pop("locked_until", None)
    return job


# -------------------------
# Producer operations
# -------------------------


async def enqueue_job(
    *,
    user_id: str,
    queue_name: str,
    payload: Dict[str, Any],
    priority: int = 0,
    max_retries: int = 3,
    run_at: Optional[str] = None,
) -> str:
    """
    Enqueue a job and record metrics.

    Returns the job_id as string UUID.
    """
    job_id = await crud.create_job(
        user_id=user_id,
        queue_name=queue_name,
        payload=payload,
        priority=priority,
        max_retries=max_retries,
        run_at=run_at,
    )

    JOBS_ENQUEUED_TOTAL.labels(queue_name=_safe_queue_label(queue_name)).inc()
    return str(job_id)


async def enqueue_batch_jobs(
    *,
    user_id: str,
    jobs: List[JobCreate],
) -> List[str]:
    """
    Enqueue multiple jobs in a single request.

    Returns list of job_ids.
    """
    job_ids = await crud.create_jobs_batch(
        user_id=user_id,
        jobs=jobs,
    )

    for job in jobs:
        JOBS_ENQUEUED_TOTAL.labels(queue_name=_safe_queue_label(job.queue_name)).inc()

    return job_ids


async def get_status(*, user_id: str, job_id: str) -> Optional[str]:
    """
    Get job status scoped to user.
    """
    return await crud.get_job_status(user_id=user_id, job_id=job_id)


async def get_detail(*, user_id: str, job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get full job detail scoped to user.
    """
    return await crud.get_job(user_id=user_id, job_id=job_id)


async def list_user_jobs(
    *,
    user_id: str,
    queue_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[list[Dict[str, Any]], int]:
    """
    List jobs for dashboards.
    """
    return await crud.list_jobs(
        user_id=user_id,
        queue_name=queue_name,
        status=status,
        limit=limit,
        offset=offset,
    )


async def cancel_pending_job(*, user_id: str, job_id: str) -> bool:
    """
    Cancel a job if pending.

    Returns True if cancelled.
    """
    ok = await crud.cancel_job(user_id=user_id, job_id=job_id)
    if ok:
        # We don't know the queue_name without an extra read.
        JOBS_CANCELLED_TOTAL.labels(queue_name="unknown").inc()
    return ok


async def queue_stats(*, user_id: str) -> list[Dict[str, Any]]:
    """
    Return per-queue stats for a user.
    """
    return await crud.get_queue_stats(user_id=user_id)


# -------------------------
# Worker operations
# -------------------------


async def lease_next(
    *,
    user_id: str,
    queue_name: str,
    worker_id: str,
    lease_seconds: int = 30,
) -> Optional[LeaseResult]:
    """
    Lease the next eligible job (pending ready or expired processing).

    Returns None if no job is available.
    """
    leased = await crud.lease_next_job(
        user_id=user_id,
        queue_name=queue_name,
        worker_id=worker_id,
        lease_seconds=lease_seconds,
    )

    qlabel = _safe_queue_label(queue_name)

    if not leased:
        JOBS_LEASE_EMPTY_TOTAL.labels(queue_name=qlabel).inc()
        return None

    # Metrics:
    JOBS_LEASED_TOTAL.labels(queue_name=qlabel).inc()

    # Best-effort recovery metric:
    # `lease_lost_count` increments when re-leasing expired jobs (see CRUD implementation).
    if leased.get("lease_lost_count"):
        LEASE_EXPIRED_RECOVERED_TOTAL.labels(queue_name=qlabel).inc()

    lease_token, lease_expires_at = _parse_lease_fields(leased)
    job = _strip_lease_fields(leased)

    return LeaseResult(
        job=job, lease_token=lease_token, lease_expires_at=lease_expires_at
    )


async def ack(
    *,
    user_id: str,
    job_id: str,
    lease_token: str,
    result: Optional[Dict[str, Any]] = None,
    queue_name_for_metrics: Optional[str] = None,
) -> bool:
    """
    Acknowledge job completion.

    Returns True if state update succeeded (token matched and job was processing).
    """
    ok = await crud.ack_job(
        user_id=user_id,
        job_id=job_id,
        lease_token=lease_token,
        result=result,
    )

    if ok:
        JOBS_ACKED_TOTAL.labels(
            queue_name=_safe_queue_label(queue_name_for_metrics)
        ).inc()
    return ok


async def nack(
    *,
    user_id: str,
    job_id: str,
    lease_token: str,
    error: str,
    retry: bool = True,
    queue_name_for_metrics: Optional[str] = None,
) -> bool:
    """
    Negative-acknowledge a job.

    Current behavior (implemented in CRUD):
    - If retry=True and retry_count < max_retries:
        status -> pending
        retry_count += 1
        run_at -> NOW() + backoff
    - Else:
        status -> dead (DLQ)
        dead_at/dead_reason populated

    Returns True if state update succeeded.
    """
    ok = await crud.nack_job(
        user_id=user_id,
        job_id=job_id,
        lease_token=lease_token,
        error=error,
        retry=retry,
    )

    qlabel = _safe_queue_label(queue_name_for_metrics)
    if ok:
        # We can't know whether it was requeued vs DLQ without re-reading the row.
        # Record a general nack. If you need exact accounting, add CRUD to return outcome.
        JOBS_NACKED_TOTAL.labels(queue_name=qlabel, outcome="nack").inc()

        # Best-effort DLQ metric when retry is disabled by request.
        if not retry:
            JOBS_MOVED_TO_DLQ_TOTAL.labels(
                queue_name=qlabel, reason="retry_disabled"
            ).inc()

    return ok


async def heartbeat(
    *,
    user_id: str,
    job_id: str,
    lease_token: str,
    lease_seconds: int = 30,
) -> bool:
    """
    Extend a job lease for long-running processing.

    Returns True if lease was extended.
    """
    return await crud.heartbeat_job(
        user_id=user_id,
        job_id=job_id,
        lease_token=lease_token,
        lease_seconds=lease_seconds,
    )
