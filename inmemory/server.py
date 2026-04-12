"""
In-Memory OpenQueue FastAPI Server
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi import FastAPI as FastAPIApp
from pydantic import BaseModel

from models import Job, JobStatus, LeasedJob, QueueStats
from store import queue_store


class JobCreate(BaseModel):
    queue_name: str = "default"
    payload: Dict[str, Any]
    priority: int = 0
    max_retries: int = 3
    run_at: Optional[str] = None


class JobBatchCreate(BaseModel):
    jobs: List[JobCreate]


class JobResponse(BaseModel):
    id: str
    queue_name: str
    status: str
    priority: int
    payload: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error_text: Optional[str] = None
    retry_count: Optional[int] = None
    max_retries: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class LeaseRequest(BaseModel):
    worker_id: str
    lease_seconds: int = 30


class LeaseResponse(BaseModel):
    job: JobResponse
    lease_token: str
    lease_expires_at: str


class HeartbeatRequest(BaseModel):
    lease_token: str
    lease_seconds: int = 30


class AckRequest(BaseModel):
    lease_token: str
    result: Optional[Dict[str, Any]] = None


class NackRequest(BaseModel):
    lease_token: str
    error: str
    retry: bool = True


router = APIRouter()


async def get_current_user() -> Dict[str, str]:
    return {"id": "default", "token": "dev-token"}


@router.post(
    "/jobs",
    summary="Enqueue a job",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def create_job_endpoint(job: JobCreate) -> dict:
    run_at = None
    if job.run_at:
        run_at = datetime.fromisoformat(job.run_at.replace("Z", "+00:00"))

    job_id = await queue_store.enqueue(
        queue_name=job.queue_name,
        payload=job.payload,
        user_id="default",
        priority=job.priority,
        max_retries=job.max_retries,
        run_at=run_at,
    )
    return {"job_id": job_id, "status": "queued"}


@router.post(
    "/jobs/batch",
    summary="Enqueue multiple jobs",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def create_batch_jobs_endpoint(batch: JobBatchCreate) -> dict:
    jobs = [job.model_dump() for job in batch.jobs]
    job_ids = await queue_store.enqueue_batch(jobs, "default")
    return {"job_ids": job_ids, "count": len(job_ids)}


@router.get("/jobs/{job_id}", summary="Get job status", response_model=dict)
async def job_status_endpoint(job_id: str) -> dict:
    status_value = await queue_store.get_status(job_id)
    if not status_value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return {"job_id": job_id, "status": status_value}


@router.get(
    "/jobs/{job_id}/detail", summary="Get job details", response_model=JobResponse
)
async def job_detail_endpoint(job_id: str) -> JobResponse:
    job = await queue_store.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return JobResponse(
        id=job.id,
        queue_name=job.queue_name,
        status=job.status.value,
        priority=job.priority,
        payload=job.payload,
        result=job.result,
        error_text=job.error_text,
        retry_count=job.retry_count,
        max_retries=job.max_retries,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
    )


@router.get("/jobs", summary="List jobs", response_model=dict)
async def list_jobs_endpoint(
    queue_name: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    items, total = await queue_store.list_jobs(
        user_id="default",
        queue_name=queue_name,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [
            JobResponse(
                id=j.id,
                queue_name=j.queue_name,
                status=j.status.value,
                priority=j.priority,
                payload=j.payload,
            )
            for j in items
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post(
    "/jobs/{job_id}/cancel",
    summary="Cancel a pending job",
    response_model=dict,
)
async def cancel_job_endpoint(job_id: str) -> dict:
    ok = await queue_store.cancel_job(job_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or not cancellable",
        )
    return {"job_id": job_id, "status": "cancelled"}


@router.post(
    "/queues/{queue_name}/lease",
    summary="Lease next job in queue",
    response_model=Optional[LeaseResponse],
)
async def lease_endpoint(queue_name: str, req: LeaseRequest) -> Optional[LeaseResponse]:
    leased = await queue_store.lease(
        queue_name=queue_name,
        worker_id=req.worker_id,
        lease_seconds=req.lease_seconds,
        user_id="default",
    )
    if not leased:
        return None

    return LeaseResponse(
        job=JobResponse(
            id=leased.job.id,
            queue_name=leased.job.queue_name,
            status=leased.job.status.value,
            priority=leased.job.priority,
            payload=leased.job.payload,
            retry_count=leased.job.retry_count,
            max_retries=leased.job.max_retries,
        ),
        lease_token=leased.lease_token,
        lease_expires_at=leased.lease_expires_at.isoformat(),
    )


@router.post(
    "/jobs/{job_id}/ack",
    summary="Acknowledge job completion",
    response_model=dict,
)
async def ack_endpoint(job_id: str, req: AckRequest) -> dict:
    ok = await queue_store.ack(
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
    response_model=dict,
)
async def nack_endpoint(job_id: str, req: NackRequest) -> dict:
    ok = await queue_store.nack(
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
    response_model=dict,
)
async def heartbeat_endpoint(job_id: str, req: HeartbeatRequest) -> dict:
    ok = await queue_store.heartbeat(
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


@router.get(
    "/dashboard/queues",
    summary="Queue statistics",
    response_model=list[dict],
)
async def dashboard_queues_endpoint() -> list[dict]:
    stats = await queue_store.queue_stats(user_id="default")
    return [s.to_dict() for s in stats]


@router.get("/health")
async def health_check():
    return {"status": "healthy", "storage": "in-memory"}


@router.get("/ready")
async def readiness_check():
    return {"status": "ready"}


def create_app() -> FastAPIApp:
    @asynccontextmanager
    async def lifespan(app):
        import asyncio

        async def recovery_loop():
            while True:
                await queue_store.recover_expired_leases()
                await asyncio.sleep(10)

        task = asyncio.create_task(recovery_loop())
        yield
        task.cancel()

    app = FastAPIApp(
        title="OpenQueue In-Memory",
        description="In-memory job queue server",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)