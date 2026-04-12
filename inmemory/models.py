"""
In-Memory OpenQueue Data Models
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD = "dead"


@dataclass
class Job:
    id: str
    queue_name: str
    payload: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    priority: int = 0
    max_retries: int = 3
    retry_count: int = 0

    run_at: Optional[datetime] = None

    locked_until: Optional[datetime] = None
    locked_by: Optional[str] = None
    lease_token: Optional[str] = None

    result: Optional[Dict[str, Any]] = None
    error_text: Optional[str] = None

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    dead_at: Optional[datetime] = None
    dead_reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "queue_name": self.queue_name,
            "status": self.status.value,
            "priority": self.priority,
            "payload": self.payload,
            "result": self.result,
            "error_text": self.error_text,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "run_at": self.run_at.isoformat() if self.run_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }


@dataclass
class LeasedJob:
    job: Job
    lease_token: str
    lease_expires_at: datetime


@dataclass
class QueueStats:
    queue_name: str
    pending: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0

    def to_dict(self) -> dict:
        return {
            "queue_name": self.queue_name,
            "pending": self.pending,
            "processing": self.processing,
            "completed": self.completed,
            "failed": self.failed,
        }