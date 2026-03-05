from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from ..deps import AuthUserDep, RateLimitEnqueueDep, RateLimitListJobsDep
from ..models import JobBatchCreate, JobCreate, JobListResponse, JobResponse
from ..services.jobs_service import (
    cancel_pending_job,
    enqueue_batch_jobs,
    enqueue_job,
    get_detail,
    get_status,
    list_user_jobs,
)

router = APIRouter(prefix="/jobs", tags=["Jobs (Producer)"])


@router.post(
    "",
    summary="Enqueue a job",
    description="Create a new job in a named queue.",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def create_job_endpoint(
    job: JobCreate,
    user: AuthUserDep,
    _: RateLimitEnqueueDep,
) -> dict:
    job_id = await enqueue_job(
        user_id=user["id"],
        queue_name=job.queue_name,
        payload=job.payload,
        priority=job.priority,
        max_retries=job.max_retries,
        run_at=job.run_at,
    )
    return {"job_id": job_id, "status": "queued"}


@router.post(
    "/batch",
    summary="Enqueue multiple jobs",
    description="Create multiple jobs in a single request for better performance.",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def create_batch_jobs_endpoint(
    batch: JobBatchCreate,
    user: AuthUserDep,
    _: RateLimitEnqueueDep,
) -> dict:
    job_ids = await enqueue_batch_jobs(
        user_id=user["id"],
        jobs=batch.jobs,
    )
    return {"job_ids": job_ids, "count": len(job_ids)}


@router.get(
    "/{job_id}",
    summary="Get job status",
    description="Return only the current status for a job belonging to the authenticated user.",
    response_model=dict,
)
async def job_status_endpoint(job_id: str, user: AuthUserDep) -> dict:
    status_value = await get_status(user_id=user["id"], job_id=job_id)
    if not status_value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return {"job_id": job_id, "status": status_value}


@router.get(
    "/{job_id}/detail",
    summary="Get job details",
    description="Return full job details (payload/result/error and timestamps).",
    response_model=JobResponse,
)
async def job_detail_endpoint(job_id: str, user: AuthUserDep) -> JobResponse:
    job = await get_detail(user_id=user["id"], job_id=job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return JobResponse.model_validate(job)


@router.get(
    "",
    summary="List jobs",
    description="List jobs for the authenticated user with optional filters and pagination.",
    response_model=JobListResponse,
)
async def list_jobs_endpoint(
    user: AuthUserDep,
    _: RateLimitListJobsDep,
    queue_name: Optional[str] = Query(default=None, description="Filter by queue name"),
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter by job status (e.g. pending, processing, completed, failed, cancelled, dead)",
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Max items to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
) -> JobListResponse:
    items, total = await list_user_jobs(
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


@router.post(
    "/{job_id}/cancel",
    summary="Cancel a pending job",
    description="Cancels a job only if it is still pending.",
    response_model=dict,
)
async def cancel_job_endpoint(job_id: str, user: AuthUserDep) -> dict:
    ok = await cancel_pending_job(user_id=user["id"], job_id=job_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or not cancellable",
        )
    return {"job_id": job_id, "status": "cancelled"}
