"""
Defining the Pydantic Schemas here
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD = "dead"


class JobCreate(BaseModel):
    """
    Pydantic Schemas for Job Creation
    """

    queue_name: str = Field(
        default="default", description="The name of the queue to which the job belongs"
    )

    payload: Dict[str, Any] = Field(
        ...,
        description="The data associated with the job, can be any JSON-serializable object",
    )

    priority: int = Field(
        default=0,
        description="The priority of the job, higher values indicate higher priority",
    )

    max_retries: int = Field(
        default=3, description="The maximum number of retries allowed for the job"
    )

    run_at: Optional[str] = Field(
        default=None,
        description="Schedule job to run at specific time (ISO 8601 datetime). If not provided, job runs immediately.",
    )


class JobBatchCreate(BaseModel):
    """
    Pydantic Schema for batch job creation
    """

    jobs: List[JobCreate] = Field(
        ..., description="List of jobs to enqueue in a single request"
    )


class JobResponse(BaseModel):
    """
    Pydantic Schema for Job Response structure
    """

    id: str = Field(..., description="The unique identifier of the job")
    queue_name: str = Field(
        ..., description="The name of the queue to which the job belongs"
    )
    status: JobStatus = Field(..., description="The current status of the job")
    priority: int = Field(
        default=0, description="Higher values indicate higher priority"
    )
    payload: Optional[Dict[str, Any]] = Field(
        default=None, description="The job payload"
    )
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="The job result (if completed)"
    )
    error_text: Optional[str] = Field(
        default=None, description="Error text (if failed)"
    )
    retry_count: Optional[int] = Field(
        default=None, description="Number of retries attempted"
    )
    max_retries: Optional[int] = Field(
        default=None, description="Maximum retries allowed"
    )
    created_at: Optional[str] = Field(
        default=None, description="Creation timestamp (ISO string)"
    )
    updated_at: Optional[str] = Field(
        default=None, description="Update timestamp (ISO string)"
    )
    started_at: Optional[str] = Field(
        default=None, description="Processing start timestamp (ISO string)"
    )
    finished_at: Optional[str] = Field(
        default=None, description="Finished timestamp (ISO string)"
    )


class LeaseRequest(BaseModel):
    """
    Worker pulls the next job from a queue.
    """

    worker_id: str = Field(..., description="Worker identifier (any string)")
    lease_seconds: int = Field(
        default=30, ge=1, le=3600, description="Lease duration in seconds"
    )


class LeaseResponse(BaseModel):
    """
    Returned to the worker when a job is leased.
    """

    job: JobResponse = Field(..., description="Leased job")
    lease_token: str = Field(
        ..., description="Opaque lease token required for ack/nack"
    )
    lease_expires_at: str = Field(
        ..., description="Lease expiry timestamp (ISO string)"
    )


class HeartbeatRequest(BaseModel):
    """
    Worker heartbeat to extend a lease for long-running jobs.
    """

    lease_token: str = Field(
        ..., description="Lease token returned by the lease endpoint"
    )
    lease_seconds: int = Field(
        default=30,
        ge=1,
        le=3600,
        description="New lease duration (seconds) starting from now",
    )


class AckRequest(BaseModel):
    """
    Worker acknowledges completion of a job.
    """

    lease_token: str = Field(..., description="Lease token returned by lease endpoint")
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional result payload"
    )


class NackRequest(BaseModel):
    """
    Worker reports failure of a job.
    """

    lease_token: str = Field(..., description="Lease token returned by lease endpoint")
    error: str = Field(..., description="Error message")
    retry: bool = Field(
        default=True, description="Whether to retry the job if retries remain"
    )


class JobListResponse(BaseModel):
    """
    Paginated job list response for dashboards.
    """

    items: List[JobResponse]
    total: int
    limit: int
    offset: int
