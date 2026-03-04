from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, status

from ..deps import (
    AuthUserDep,
    RateLimitAckDep,
    RateLimitHeartbeatDep,
    RateLimitLeaseDep,
    RateLimitNackDep,
)
from ..models import (
    AckRequest,
    HeartbeatRequest,
    JobResponse,
    LeaseRequest,
    LeaseResponse,
    NackRequest,
)
from ..services.jobs_service import ack, heartbeat, lease_next, nack

router = APIRouter(tags=["Workers (BYOW)"])


@router.post(
    "/queues/{queue_name}/lease",
    summary="Lease next job in queue",
    description=(
        "Atomically claim the next available job in a queue and return it with a lease token.\n\n"
        "Eligibility rules:\n"
        "- pending jobs where run_at <= now()\n"
        "- processing jobs where locked_until < now() (expired lease / visibility timeout recovery)\n\n"
        "If no job is available, returns null.\n\n"
        "The lease token must be used for ack/nack/heartbeat."
    ),
    response_model=Optional[LeaseResponse],
)
async def lease_endpoint(
    queue_name: str,
    req: LeaseRequest,
    user: AuthUserDep,
    _: RateLimitLeaseDep,
) -> Optional[LeaseResponse]:
    res = await lease_next(
        user_id=user["id"],
        queue_name=queue_name,
        worker_id=req.worker_id,
        lease_seconds=req.lease_seconds,
    )
    if res is None:
        return None

    return LeaseResponse(
        job=JobResponse.model_validate(res.job),
        lease_token=res.lease_token,
        lease_expires_at=res.lease_expires_at,
    )


@router.post(
    "/jobs/{job_id}/ack",
    summary="Acknowledge job completion",
    description="Completes a leased job. Requires the lease_token returned by the lease endpoint.",
    response_model=dict,
)
async def ack_endpoint(
    job_id: str,
    req: AckRequest,
    user: AuthUserDep,
    _: RateLimitAckDep,
) -> dict:
    ok = await ack(
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
    return {"job_id": job_id, "status": "completed"}


@router.post(
    "/jobs/{job_id}/nack",
    summary="Negative-acknowledge a job",
    description=(
        "Marks a leased job as failed.\n\n"
        "If retry=true and retries remain, the job is requeued using backoff via run_at.\n"
        "If retries are exhausted (or retry=false), the job is moved to the DLQ (dead)."
    ),
    response_model=dict,
)
async def nack_endpoint(
    job_id: str,
    req: NackRequest,
    user: AuthUserDep,
    _: RateLimitNackDep,
) -> dict:
    ok = await nack(
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
    return {"job_id": job_id, "status": "failed_or_requeued"}


@router.post(
    "/jobs/{job_id}/heartbeat",
    summary="Extend a job lease (heartbeat)",
    description=(
        "Extends the lease for a long-running job. Requires the current lease_token.\n\n"
        "Use this periodically for jobs that take longer than the original lease duration."
    ),
    response_model=dict,
)
async def heartbeat_endpoint(
    job_id: str,
    req: HeartbeatRequest,
    user: AuthUserDep,
    _: RateLimitHeartbeatDep,
) -> dict:
    ok = await heartbeat(
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
    return {"job_id": job_id, "status": "lease_extended"}
