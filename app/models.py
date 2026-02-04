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
        description="The priority of the job, lower values indicate higher priority",
    )

    max_retries: int = Field(
        default=3, description="The maximum number of retries allowed for the job"
    )


class JobResponse(BaseModel):
    """
    Pydantic Schema for Job Respose structure
    """

    id: str = Field(..., description="The unique identifier of the job")

    queue_name: str = Field(
        default="default", description="The name of the queue to which the job belongs"
    )

    status: JobStatus = Field(..., description="The current status of the job")

    priority: int = Field(
        default=0,
        description="The priority of the job, lower values indicate higher priority",
    )

    payload: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The data associated with the job, can be any JSON-serializable object",
    )
