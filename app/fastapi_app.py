import uuid

from fastapi import FastAPI
from fastapi.routing import Dict
from starlette.exceptions import HTTPException

from .crud import create_job, get_job_status, get_next_job, update_job_result
from .models import JobCreate, JobResponse

app = FastAPI(title="OpenQueue", version="1.0.0")


@app.post("/jobs", response_model=dict)
async def job_create(job: JobCreate):
    """
    Endpoint to create a new job in the queue
    """
    job_id = await create_job(
        job.queue_name, job.payload, job.priority, job.max_retries
    )

    return {"job_id": job_id, "status": "queued"}


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    status = await get_job_status(job_id)

    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "status": status}
