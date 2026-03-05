"""
OpenQueue SDK Tests
"""

import pytest
import time
from openqueue import OpenQueue
from openqueue.models import JobStatus


BASE_URL = "http://localhost:8000"
API_TOKEN = "oq_live_qXxA5liMxzRhz3uVTFYziaQSrw8tB05y2hU5O7VivyA"


@pytest.fixture
def client():
    """Create a test client."""
    with OpenQueue(BASE_URL, API_TOKEN, timeout=10.0) as c:
        yield c


class TestProducerAPI:
    """Test producer methods."""

    def test_enqueue_simple_job(self, client):
        """Test enqueuing a basic job."""
        job_id = client.enqueue(
            queue_name="test-queue",
            payload={"task": "test", "data": "hello"},
        )
        assert job_id is not None
        assert isinstance(job_id, str)

    def test_enqueue_with_priority(self, client):
        """Test enqueuing with priority."""
        job_id = client.enqueue(
            queue_name="test-queue",
            payload={"task": "priority"},
            priority=10,
            max_retries=5,
        )
        assert job_id is not None

    def test_get_status(self, client):
        """Test getting job status."""
        job_id = client.enqueue(queue_name="test-queue", payload={"task": "test"})
        status = client.get_status(job_id)
        assert status in [s.value for s in JobStatus]

    def test_get_job(self, client):
        """Test getting full job details."""
        payload = {"task": "full_test", "value": 123}
        job_id = client.enqueue(queue_name="test-queue", payload=payload)
        
        job = client.get_job(job_id)
        assert job.id == job_id
        assert job.queue_name == "test-queue"
        assert job.status == JobStatus.PENDING
        assert job.payload == payload

    def test_list_jobs(self, client):
        """Test listing jobs."""
        # Enqueue a few jobs
        for i in range(3):
            client.enqueue(queue_name="list-test", payload={"i": i})

        jobs = client.list_jobs(queue_name="list-test", limit=10)
        assert jobs.total >= 3
        assert len(jobs.items) >= 3
        assert jobs.limit == 10
        assert jobs.offset == 0

    def test_cancel_job(self, client):
        """Test cancelling a pending job."""
        job_id = client.enqueue(queue_name="test-queue", payload={"task": "cancel"})
        
        # Cancel should succeed
        result = client.cancel_job(job_id)
        assert result is True
        
        # Cancelling again should fail (not found/invalid state)
        result = client.cancel_job(job_id)
        assert result is False

    def test_list_jobs_with_status_filter(self, client):
        """Test filtering jobs by status."""
        job_id = client.enqueue(queue_name="filter-test", payload={"task": "filter"})
        
        pending_jobs = client.list_jobs(queue_name="filter-test", status="pending")
        assert any(j.id == job_id for j in pending_jobs.items)


class TestWorkerAPI:
    """Test worker methods."""

    def test_lease_empty_queue(self, client):
        """Test leasing from empty queue returns None."""
        leased = client.lease(
            queue_name=f"nonexistent-queue-{time.time()}",
            worker_id="test-worker",
            lease_seconds=30,
        )
        assert leased is None

    def test_lease_and_ack(self, client):
        """Test full lease -> process -> ack cycle."""
        # Use unique queue name for test isolation
        queue = f"worker-test-{time.time()}"
        
        # Enqueue a job
        job_id = client.enqueue(queue_name=queue, payload={"task": "process"})
        
        # Lease the job
        leased = client.lease(queue_name=queue, worker_id="test-worker")
        assert leased is not None
        # Note: Job might not be the same if there are other jobs in queue
        assert leased.lease_token is not None
        
        # Acknowledge completion
        result = {"processed": True, "output": "done"}
        ack_result = client.ack(leased.job.id, leased.lease_token, result=result)
        assert ack_result is True
        
        # Verify job is completed
        job = client.get_job(leased.job.id)
        assert job.status == JobStatus.COMPLETED
        assert job.result == result

    def test_lease_and_nack_with_retry(self, client):
        """Test nack with retry requeues job."""
        queue = f"nack-test-{time.time()}"
        job_id = client.enqueue(queue_name=queue, payload={"task": "fail"})
        
        leased = client.lease(queue_name=queue, worker_id="test-worker")
        assert leased is not None
        
        # Nack with retry
        client.nack(
            leased.job.id,
            leased.lease_token,
            error="Temporary error",
            retry=True,
        )
        
        # Job should be back to pending
        job = client.get_job(leased.job.id)
        assert job.status == JobStatus.PENDING

    def test_lease_and_nack_no_retry(self, client):
        """Test nack without retry moves to dead."""
        queue = f"nack-no-retry-{time.time()}"
        job_id = client.enqueue(
            queue_name=queue,
            payload={"task": "fail"},
            max_retries=0,
        )
        
        leased = client.lease(queue_name=queue, worker_id="test-worker")
        assert leased is not None
        
        # Nack without retry
        client.nack(
            leased.job.id,
            leased.lease_token,
            error="Permanent error",
            retry=False,
        )
        
        # Job should be dead
        job = client.get_job(leased.job.id)
        assert job.status == JobStatus.DEAD

    def test_heartbeat(self, client):
        """Test heartbeat extends lease."""
        queue = f"heartbeat-test-{time.time()}"
        job_id = client.enqueue(queue_name=queue, payload={"task": "long"})
        
        leased = client.lease(queue_name=queue, worker_id="test-worker")
        assert leased is not None
        
        # Send heartbeat
        result = client.heartbeat(leased.job.id, leased.lease_token, lease_seconds=60)
        assert result is True

    def test_invalid_lease_token(self, client):
        """Test invalid lease token fails."""
        queue = f"invalid-test-{time.time()}"
        job_id = client.enqueue(queue_name=queue, payload={"task": "test"})
        
        leased = client.lease(queue_name=queue, worker_id="test-worker")
        assert leased is not None
        
        # Try to ack with wrong token - should raise LeaseTokenError
        from openqueue.exceptions import LeaseTokenError
        with pytest.raises(LeaseTokenError):
            client.ack(leased.job.id, "invalid-token-123", result={})


class TestDashboardAPI:
    """Test dashboard methods."""

    def test_get_queue_stats(self, client):
        """Test getting queue statistics."""
        # Enqueue some jobs
        client.enqueue(queue_name="stats-test", payload={"task": "1"})
        client.enqueue(queue_name="stats-test", payload={"task": "2"})
        
        stats = client.get_queue_stats()
        assert isinstance(stats, list)
        
        # Find our test queue
        test_stats = [s for s in stats if s.queue_name == "stats-test"]
        if test_stats:
            assert test_stats[0].total >= 2


class TestErrorHandling:
    """Test error handling."""

    def test_invalid_token(self):
        """Test authentication error."""
        from openqueue.exceptions import AuthenticationError
        
        with pytest.raises(AuthenticationError):
            client = OpenQueue(BASE_URL, "invalid-token")
            client.enqueue("test", {"task": "test"})

    def test_job_not_found(self, client):
        """Test job not found error."""
        from openqueue.exceptions import JobNotFoundError
        
        with pytest.raises(JobNotFoundError):
            client.get_job("00000000-0000-0000-0000-000000000000")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
