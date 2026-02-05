from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query

from .auth import CurrentUser, get_current_user
from .crud import (
    ack_job,
    cancel_job,
    create_job,
    get_job,
    get_job_status,
    get_queue_stats,
    lease_next_job,
    list_jobs,
    nack_job,
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

app = FastAPI(title="OpenQueue", version="0.0.1")


@app.post("/jobs", response_model=dict)
async def job_create(job: JobCreate, user: CurrentUser = Depends(get_current_user)):
    job_id = await create_job(
        user_id=user["id"],
        queue_name=job.queue_name,
        payload=job.payload,
        priority=job.priority,
        max_retries=job.max_retries,
    )
    return {"job_id": str(job_id), "status": "queued"}


@app.get("/jobs/{job_id}", response_model=dict)
async def job_status(job_id: str, user: CurrentUser = Depends(get_current_user)):
    status = await get_job_status(user_id=user["id"], job_id=job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "status": status}


@app.get("/jobs/{job_id}/detail", response_model=JobResponse)
async def job_get(job_id: str, user: CurrentUser = Depends(get_current_user)):
    job = await get_job(user_id=user["id"], job_id=job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/jobs", response_model=JobListResponse)
async def jobs_list(
    user: CurrentUser = Depends(get_current_user),
    queue_name: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    items, total = await list_jobs(
        user_id=user["id"],
        queue_name=queue_name,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@app.post("/jobs/{job_id}/cancel", response_model=dict)
async def job_cancel(job_id: str, user: CurrentUser = Depends(get_current_user)):
    ok = await cancel_job(user_id=user["id"], job_id=job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found or not cancellable")
    return {"job_id": job_id, "status": "cancelled"}


@app.post("/queues/{queue_name}/lease", response_model=Optional[LeaseResponse])
async def queue_lease(
    queue_name: str,
    req: LeaseRequest,
    user: CurrentUser = Depends(get_current_user),
):
    leased = await lease_next_job(
        user_id=user["id"],
        queue_name=queue_name,
        worker_id=req.worker_id,
        lease_seconds=req.lease_seconds,
    )
    if not leased:
        # Return null when no jobs are available (simpler for clients than 204 + empty body)
        return None

    lease_token = leased.get("lease_token")
    lease_expires_at = leased.get("locked_until")
    if not lease_token or not lease_expires_at:
        raise HTTPException(
            status_code=500, detail="Lease created but missing lease metadata"
        )

    job = dict(leased)
    job.pop("lease_token", None)
    job.pop("locked_until", None)

    return {
        "job": job,
        "lease_token": str(lease_token),
        "lease_expires_at": str(lease_expires_at),
    }


@app.post("/jobs/{job_id}/ack", response_model=dict)
async def job_ack(
    job_id: str, req: AckRequest, user: CurrentUser = Depends(get_current_user)
):
    ok = await ack_job(
        user_id=user["id"],
        job_id=job_id,
        lease_token=req.lease_token,
        result=req.result,
    )
    if not ok:
        raise HTTPException(
            status_code=409, detail="Job not found, not leased, or lease token mismatch"
        )
    return {"job_id": job_id, "status": "completed"}


@app.post("/jobs/{job_id}/nack", response_model=dict)
async def job_nack(
    job_id: str, req: NackRequest, user: CurrentUser = Depends(get_current_user)
):
    ok = await nack_job(
        user_id=user["id"],
        job_id=job_id,
        lease_token=req.lease_token,
        error=req.error,
        retry=req.retry,
    )
    if not ok:
        raise HTTPException(
            status_code=409, detail="Job not found, not leased, or lease token mismatch"
        )
    return {"job_id": job_id, "status": "failed_or_requeued"}


@app.get("/dashboard/queues", response_model=list[dict])
async def dashboard_queues(user: CurrentUser = Depends(get_current_user)):
    return await get_queue_stats(user_id=user["id"])
