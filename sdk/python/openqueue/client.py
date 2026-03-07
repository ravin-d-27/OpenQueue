"""
OpenQueue Python client.
"""

import time
from typing import Any, Dict, List, Optional

import httpx

from .exceptions import (
    AuthenticationError,
    JobNotFoundError,
    LeaseTokenError,
    OpenQueueError,
    RateLimitError,
    ValidationError,
)
from .models import Job, JobListResponse, LeasedJob, QueueStats


class OpenQueue:
    """
    Python client for OpenQueue.

    Usage:
        # As a producer
        client = OpenQueue("https://queue.example.com", "your-api-token")
        job_id = client.enqueue("my-queue", {"task": "do_something"})

        # As a worker
        leased = client.lease("my-queue", "worker-1")
        # ... process job ...
        client.ack(leased.job.id, leased.lease_token, result={"done": True})
    """

    def __init__(
        self,
        base_url: str,
        api_token: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        max_connections: int = 10,
        max_keepalive_connections: int = 5,
    ):
        """
        Initialize the OpenQueue client.

        Args:
            base_url: The base URL of the OpenQueue API (e.g., https://queue.example.com)
            api_token: Your API token for authentication
            timeout: Request timeout in seconds (default: 30)
            max_retries: Number of retries for transient errors (default: 3)
            max_connections: Maximum number of connections in the pool (default: 10)
            max_keepalive_connections: Maximum keepalive connections (default: 5)
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout = timeout
        self.max_retries = max_retries

        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
            ),
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
        )

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request with error handling."""
        response: Optional[httpx.Response] = None
        for attempt in range(self.max_retries):
            try:
                response = self._client.request(
                    method=method, url=path, params=params, json=json
                )
                break
            except httpx.TimeoutException:
                if attempt == self.max_retries - 1:
                    raise OpenQueueError("Request timed out")
                time.sleep(0.5 * (attempt + 1))
            except httpx.ConnectError:
                if attempt == self.max_retries - 1:
                    raise OpenQueueError("Connection failed")
                time.sleep(0.5 * (attempt + 1))

        if response is None:
            raise OpenQueueError("Request failed")

        if response.status_code == 401:
            raise AuthenticationError("Invalid API token")
        if response.status_code == 422:
            raise ValidationError(f"Validation error: {response.text[:100]}")
        if response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        if response.status_code == 404:
            raise JobNotFoundError("Job not found")
        if response.status_code == 409:
            raise LeaseTokenError("Lease token mismatch or job not in processing state")
        if response.status_code >= 500:
            raise OpenQueueError(f"Server error: {response.status_code} - {response.text[:100]}")
        if response.status_code == 400 and "lease" in response.text.lower():
            raise LeaseTokenError("Invalid lease token")

        response.raise_for_status()
        return response.json()

    # ==================== Producer API ====================

    def enqueue(
        self,
        queue_name: str,
        payload: Dict[str, Any],
        priority: int = 0,
        max_retries: int = 3,
        run_at: Optional[str] = None,
    ) -> str:
        """
        Enqueue a new job.

        Args:
            queue_name: The name of the queue
            payload: The job payload (any JSON-serializable dict)
            priority: Job priority (higher = higher priority, default: 0)
            max_retries: Maximum number of retries on failure (default: 3)
            run_at: Schedule job to run at specific time (ISO 8601 datetime string, e.g., "2024-01-01T12:00:00Z")

        Returns:
            The job ID
        """
        data = {
            "queue_name": queue_name,
            "payload": payload,
            "priority": priority,
            "max_retries": max_retries,
        }
        if run_at:
            data["run_at"] = run_at.replace("Z", "+00:00")

        result = self._request("POST", "/jobs", json=data)
        return result["job_id"]

    def enqueue_batch(
        self,
        jobs: List[Dict[str, Any]],
    ) -> List[str]:
        """
        Enqueue multiple jobs in a single request for better performance.

        Args:
            jobs: List of job dictionaries. Each dict should have:
                - queue_name: str (required)
                - payload: Dict[str, Any] (required)
                - priority: int (optional, default: 0)
                - max_retries: int (optional, default: 3)
                - run_at: str (optional, ISO 8601 datetime)

        Returns:
            List of job IDs in the same order as input jobs
        """
        formatted_jobs = []
        for job in jobs:
            formatted_job = {
                "queue_name": job["queue_name"],
                "payload": job["payload"],
                "priority": job.get("priority", 0),
                "max_retries": job.get("max_retries", 3),
            }
            if job.get("run_at"):
                formatted_job["run_at"] = job["run_at"].replace("Z", "+00:00")
            formatted_jobs.append(formatted_job)

        result = self._request("POST", "/jobs/batch", json={"jobs": formatted_jobs})
        return result["job_ids"]

    def get_status(self, job_id: str) -> str:
        """
        Get the status of a job.

        Args:
            job_id: The job ID

        Returns:
            The job status (e.g., "pending", "processing", "completed")
        """
        result = self._request("GET", f"/jobs/{job_id}")
        return result["status"]

    def get_job(self, job_id: str) -> Job:
        """
        Get full details of a job.

        Args:
            job_id: The job ID

        Returns:
            Job object with full details
        """
        data = self._request("GET", f"/jobs/{job_id}/detail")
        return Job.from_dict(data)

    def list_jobs(
        self,
        queue_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> JobListResponse:
        """
        List jobs with optional filters.

        Args:
            queue_name: Filter by queue name
            status: Filter by job status
            limit: Maximum number of jobs to return (max: 200)
            offset: Pagination offset

        Returns:
            JobListResponse with items and pagination info
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if queue_name:
            params["queue_name"] = queue_name
        if status:
            params["status"] = status

        data = self._request("GET", "/jobs", params=params)
        return JobListResponse(
            items=[Job.from_dict(item) for item in data["items"]],
            total=data["total"],
            limit=data["limit"],
            offset=data["offset"],
        )

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a pending job.

        Args:
            job_id: The job ID

        Returns:
            True if cancelled, False otherwise
        """
        try:
            self._request("POST", f"/jobs/{job_id}/cancel")
            return True
        except JobNotFoundError:
            return False

    # ==================== Worker API ====================

    def lease(
        self,
        queue_name: str,
        worker_id: str,
        lease_seconds: int = 30,
    ) -> Optional[LeasedJob]:
        """
        Lease the next available job from a queue.

        Args:
            queue_name: The name of the queue
            worker_id: Unique identifier for this worker
            lease_seconds: How long to lease the job (default: 30)

        Returns:
            LeasedJob object if a job is available, None if queue is empty
        """
        data = {"worker_id": worker_id, "lease_seconds": lease_seconds}
        result = self._request("POST", f"/queues/{queue_name}/lease", json=data)

        if result is None:
            return None

        return LeasedJob.from_dict(result)

    def ack(
        self,
        job_id: str,
        lease_token: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Acknowledge successful completion of a job.

        Args:
            job_id: The job ID
            lease_token: The lease token from the lease response
            result: Optional result payload to store with the job

        Returns:
            True if acknowledged successfully
        """
        data: Dict[str, Any] = {"lease_token": lease_token}
        if result is not None:
            data["result"] = result

        self._request("POST", f"/jobs/{job_id}/ack", json=data)
        return True

    def nack(
        self,
        job_id: str,
        lease_token: str,
        error: str,
        retry: bool = True,
    ) -> bool:
        """
        Report failure of a job.

        Args:
            job_id: The job ID
            lease_token: The lease token from the lease response
            error: Error message describing the failure
            retry: Whether to retry the job if retries remain (default: True)

        Returns:
            True if nacked successfully
        """
        data = {
            "lease_token": lease_token,
            "error": error,
            "retry": retry,
        }
        self._request("POST", f"/jobs/{job_id}/nack", json=data)
        return True

    def heartbeat(
        self,
        job_id: str,
        lease_token: str,
        lease_seconds: int = 30,
    ) -> bool:
        """
        Send a heartbeat to extend the lease on a job.

        Useful for long-running jobs that need more time than the initial lease.

        Args:
            job_id: The job ID
            lease_token: The lease token from the lease response
            lease_seconds: New lease duration in seconds

        Returns:
            True if heartbeat successful
        """
        data = {"lease_token": lease_token, "lease_seconds": lease_seconds}
        self._request("POST", f"/jobs/{job_id}/heartbeat", json=data)
        return True

    # ==================== Dashboard API ====================

    def get_queue_stats(self) -> List[QueueStats]:
        """
        Get statistics for all queues.

        Returns:
            List of QueueStats objects, one per queue
        """
        data = self._request("GET", "/dashboard/queues")
        return [QueueStats.from_dict(item) for item in data]

    # ==================== Utility ====================

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self) -> "OpenQueue":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
