"""
In-Memory OpenQueue Store
Implements a Redis-like in-memory job queue using heapq for priorities.
"""

import asyncio
import heapq
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from models import Job, JobStatus, LeasedJob, QueueStats


class InMemoryQueue:
    def __init__(self):
        self._lock = asyncio.Lock()

        self._jobs: Dict[str, Job] = {}

        self._pending_heaps: Dict[str, List[Tuple]] = {}

        self._queue_index: Dict[str, set] = {}

        self._status_index: Dict[str, Dict[str, set]] = {}

    async def enqueue(
        self,
        queue_name: str,
        payload: dict,
        user_id: str,
        priority: int = 0,
        max_retries: int = 3,
        run_at: Optional[datetime] = None,
    ) -> str:
        async with self._lock:
            job_id = str(uuid4())

            now = datetime.now(timezone.utc)
            scheduled_at = run_at or now

            job = Job(
                id=job_id,
                queue_name=queue_name,
                payload=payload,
                priority=priority,
                max_retries=max_retries,
                run_at=scheduled_at,
                created_at=now,
                updated_at=now,
            )

            self._jobs[job_id] = job

            self._index_job(queue_name, job_id, "pending")

            self._add_to_pending_heap(queue_name, job, user_id)

            return job_id

    async def enqueue_batch(
        self, jobs: List[dict], user_id: str
    ) -> List[str]:
        async with self._lock:
            job_ids = []
            now = datetime.now(timezone.utc)

            for job_data in jobs:
                job_id = str(uuid4())

                run_at = job_data.get("run_at")
                if isinstance(run_at, str):
                    run_at = datetime.fromisoformat(run_at.replace("Z", "+00:00"))
                scheduled_at = run_at or now

                job = Job(
                    id=job_id,
                    queue_name=job_data.get("queue_name", "default"),
                    payload=job_data.get("payload", {}),
                    priority=job_data.get("priority", 0),
                    max_retries=job_data.get("max_retries", 3),
                    run_at=scheduled_at,
                    created_at=now,
                    updated_at=now,
                )

                self._jobs[job_id] = job
                job_ids.append(job_id)

                self._index_job(job.queue_name, job_id, "pending")
                self._add_to_pending_heap(job.queue_name, job, user_id)

            return job_ids

    async def get_status(self, job_id: str) -> Optional[str]:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                return job.status.value
            return None

    async def get_job(self, job_id: str) -> Optional[Job]:
        async with self._lock:
            return self._jobs.get(job_id)

    async def list_jobs(
        self,
        user_id: str,
        queue_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Job], int]:
        async with self._lock:
            jobs = []

            for job in self._jobs.values():
                if job.queue_name == (queue_name or job.queue_name):
                    if status is None or job.status.value == status:
                        jobs.append(job)

            jobs.sort(key=lambda j: (-j.priority, j.created_at))

            total = len(jobs)
            items = jobs[offset : offset + limit]

            return items, total

    async def cancel_job(self, job_id: str) -> bool:
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            if job.status != JobStatus.PENDING:
                return False

            job.status = JobStatus.CANCELLED
            job.updated_at = datetime.now(timezone.utc)

            self._remove_from_pending_heap(job.queue_name, job_id)

            return True

    async def lease(
        self,
        queue_name: str,
        worker_id: str,
        lease_seconds: int = 30,
        user_id: str = "default",
    ) -> Optional[LeasedJob]:
        async with self._lock:
            now = datetime.now(timezone.utc)

            job = self._find_next_job(queue_name, user_id, now)
            if not job:
                return None

            lease_token = str(uuid4())
            lease_expires = now + timedelta(seconds=lease_seconds)

            job.status = JobStatus.PROCESSING
            job.locked_until = lease_expires
            job.locked_by = worker_id
            job.lease_token = lease_token
            job.started_at = job.started_at or now
            job.updated_at = now

            self._remove_from_pending_heap(queue_name, job.id)
            self._reindex_job_status(queue_name, job.id, "pending", "processing")

            return LeasedJob(
                job=job,
                lease_token=lease_token,
                lease_expires_at=lease_expires,
            )

    async def ack(
        self,
        job_id: str,
        lease_token: str,
        result: Optional[dict] = None,
    ) -> bool:
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            if job.lease_token != lease_token:
                return False

            now = datetime.now(timezone.utc)
            job.status = JobStatus.COMPLETED
            job.result = result
            job.finished_at = now
            job.updated_at = now

            self._reindex_job_status(
                job.queue_name, job.id, "processing", "completed"
            )

            return True

    async def nack(
        self,
        job_id: str,
        lease_token: str,
        error: str,
        retry: bool = True,
    ) -> bool:
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            if job.lease_token != lease_token:
                return False

            now = datetime.now(timezone.utc)

            if retry and job.retry_count < job.max_retries:
                job.status = JobStatus.PENDING
                job.retry_count += 1

                delay_seconds = 2**job.retry_count
                job.run_at = now + timedelta(seconds=delay_seconds)

                job.locked_until = None
                job.locked_by = None
                job.lease_token = None
                job.updated_at = now
                job.error_text = error

                self._add_to_pending_heap(job.queue_name, job, "default")
                self._reindex_job_status(
                    job.queue_name, job.id, "processing", "pending"
                )
            else:
                job.status = JobStatus.DEAD
                job.error_text = error
                job.finished_at = now
                job.updated_at = now
                job.dead_at = now
                job.dead_reason = error

                self._reindex_job_status(
                    job.queue_name, job.id, "processing", "dead"
                )

            return True

    async def heartbeat(
        self, job_id: str, lease_token: str, lease_seconds: int = 30
    ) -> bool:
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            if job.lease_token != lease_token:
                return False

            now = datetime.now(timezone.utc)
            job.locked_until = now + timedelta(seconds=lease_seconds)
            job.updated_at = now

            return True

    async def queue_stats(self, user_id: str) -> List[QueueStats]:
        async with self._lock:
            stats_map: Dict[str, QueueStats] = {}

            for job in self._jobs.values():
                if job.queue_name not in stats_map:
                    stats_map[job.queue_name] = QueueStats(queue_name=job.queue_name)

                stats = stats_map[job.queue_name]
                if job.status == JobStatus.PENDING:
                    stats.pending += 1
                elif job.status == JobStatus.PROCESSING:
                    stats.processing += 1
                elif job.status == JobStatus.COMPLETED:
                    stats.completed += 1
                elif job.status in (JobStatus.FAILED, JobStatus.DEAD):
                    stats.failed += 1

            return list(stats_map.values())

    async def recover_expired_leases(
        self, queue_name: Optional[str] = None
    ) -> int:
        async with self._lock:
            now = datetime.now(timezone.utc)
            recovered = 0

            for job in self._jobs.values():
                if job.status != JobStatus.PROCESSING:
                    continue

                if queue_name and job.queue_name != queue_name:
                    continue

                if job.locked_until and job.locked_until < now:
                    job.status = JobStatus.PENDING
                    job.locked_until = None
                    job.locked_by = None
                    job.lease_token = None
                    job.updated_at = now
                    job.retry_count += 1

                    self._reindex_job_status(
                        job.queue_name, job.id, "processing", "pending"
                    )
                    self._add_to_pending_heap(job.queue_name, job, "default")
                    recovered += 1

            return recovered

    def _find_next_job(
        self, queue_name: str, user_id: str, now: datetime
    ) -> Optional[Job]:
        heap = self._pending_heaps.get(queue_name, [])
        if not heap:
            return None

        while heap:
            priority, created_at, job_id = heap[0]

            job = self._jobs.get(job_id)
            if not job:
                heapq.heappop(heap)
                continue

            if job.status != JobStatus.PENDING:
                heapq.heappop(heap)
                continue

            if job.run_at and job.run_at > now:
                heapq.heappop(heap)
                continue

            heapq.heappop(heap)
            return job

        return None

    def _add_to_pending_heap(self, queue_name: str, job: Job, user_id: str):
        if queue_name not in self._pending_heaps:
            self._pending_heaps[queue_name] = []

        heapq.heappush(
            self._pending_heaps[queue_name],
            (-job.priority, job.created_at.timestamp(), job.id),
        )

    def _remove_from_pending_heap(self, queue_name: str, job_id: str):
        heap = self._pending_heaps.get(queue_name, [])
        new_heap = [item for item in heap if item[2] != job_id]
        heapq.heapify(new_heap)
        self._pending_heaps[queue_name] = new_heap

    def _index_job(self, queue_name: str, job_id: str, status: str):
        if queue_name not in self._queue_index:
            self._queue_index[queue_name] = set()
        self._queue_index[queue_name].add(job_id)

        key = f"{status}"
        if key not in self._status_index:
            self._status_index[key] = {}
        if queue_name not in self._status_index[key]:
            self._status_index[key][queue_name] = set()
        self._status_index[key][queue_name].add(job_id)

    def _reindex_job_status(
        self, queue_name: str, job_id: str, old_status: str, new_status: str
    ):
        old_key = f"{old_status}"
        new_key = f"{new_status}"

        if old_key in self._status_index:
            if queue_name in self._status_index[old_key]:
                self._status_index[old_key][queue_name].discard(job_id)

        if new_key not in self._status_index:
            self._status_index[new_key] = {}
        if queue_name not in self._status_index[new_key]:
            self._status_index[new_key][queue_name] = set()
        self._status_index[new_key][queue_name].add(job_id)


queue_store = InMemoryQueue()