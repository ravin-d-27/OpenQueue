"""
OpenQueue data models.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD = "dead"


@dataclass
class Job:
    """Represents a job in the queue."""

    id: str
    queue_name: str
    status: JobStatus
    priority: int = 0
    payload: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error_text: Optional[str] = None
    retry_count: Optional[int] = None
    max_retries: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        """Create a Job from API response dictionary."""
        status = data.get("status", "pending")
        if isinstance(status, str):
            status = JobStatus(status)

        return cls(
            id=data["id"],
            queue_name=data["queue_name"],
            status=status,
            priority=data.get("priority", 0),
            payload=data.get("payload"),
            result=data.get("result"),
            error_text=data.get("error_text"),
            retry_count=data.get("retry_count"),
            max_retries=data.get("max_retries"),
            created_at=_parse_datetime(data.get("created_at")),
            updated_at=_parse_datetime(data.get("updated_at")),
            started_at=_parse_datetime(data.get("started_at")),
            finished_at=_parse_datetime(data.get("finished_at")),
        )


@dataclass
class LeasedJob:
    """Represents a leased job with lease metadata."""

    job: Job
    lease_token: str
    lease_expires_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LeasedJob":
        """Create a LeasedJob from API response dictionary."""
        expires_at = _parse_datetime(data.get("lease_expires_at"))
        return cls(
            job=Job.from_dict(data["job"]),
            lease_token=data["lease_token"],
            lease_expires_at=expires_at,
        )


@dataclass
class QueueStats:
    """Statistics for a queue."""

    queue_name: str
    pending: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    dead: int = 0
    total: int = 0
    oldest_pending_created_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueueStats":
        """Create QueueStats from API response dictionary."""
        return cls(
            queue_name=data["queue_name"],
            pending=data.get("pending", 0),
            processing=data.get("processing", 0),
            completed=data.get("completed", 0),
            failed=data.get("failed", 0),
            cancelled=data.get("cancelled", 0),
            total=data.get("total", 0),
            oldest_pending_created_at=_parse_datetime(
                data.get("oldest_pending_created_at")
            ),
        )


@dataclass
class JobListResponse:
    """Paginated list of jobs."""

    items: List[Job]
    total: int
    limit: int
    offset: int


def _parse_datetime(value: Any) -> Optional[datetime]:
    """Parse datetime from ISO string or return None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None
