"""
OpenQueue SDK - Complete Usage Examples
========================================

This file provides comprehensive examples for getting started with OpenQueue.
Copy this file to your project and adapt it to your needs.

Visit: https://github.com/ravin-d-27/OpenQueue for full documentation
"""

import time

from openqueue import OpenQueue
from openqueue.exceptions import (
    AuthenticationError,
    JobNotFoundError,
    LeaseTokenError,
    OpenQueueError,
    RateLimitError,
    ValidationError,
)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Replace these with your actual values
BASE_URL = "http://localhost:8000"
API_TOKEN = "oq_live_qXxA5liMxzRhz3uVTFYziaQSrw8tB05y2hU5O7VivyA"


# =============================================================================
# EXAMPLE 1: Basic Client Initialization
# =============================================================================


def example_basic_client():
    """Basic client initialization and connection test."""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Basic Client Initialization")
    print("=" * 60)

    # Method 1: Direct initialization
    client = OpenQueue(BASE_URL, API_TOKEN)

    # Test connection by getting queue stats
    stats = client.get_queue_stats()
    print(f"Connected! Found {len(stats)} queue(s)")
    for s in stats:
        print(f"  - {s.queue_name}: {s.pending} pending, {s.processing} processing")

    # Always close the client when done
    client.close()


def example_context_manager():
    """Using context manager for automatic cleanup."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Context Manager")
    print("=" * 60)

    # Client is automatically closed when exiting the block
    with OpenQueue(BASE_URL, API_TOKEN) as client:
        stats = client.get_queue_stats()
        print(f"Connected! Found {len(stats)} queue(s)")
    # Client automatically closed here


# =============================================================================
# EXAMPLE 3: Producer - Enqueue Jobs
# =============================================================================


def example_producer():
    """Producer examples - creating and managing jobs."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Producer - Enqueue Jobs")
    print("=" * 60)

    with OpenQueue(BASE_URL, API_TOKEN) as client:
        # --- Basic job enqueue ---
        job_id = client.enqueue(
            queue_name="emails",
            payload={"to": "user@example.com", "subject": "Hello"},
        )
        print(f"Enqueued basic job: {job_id}")

        # --- High priority job ---
        priority_job_id = client.enqueue(
            queue_name="emails",
            payload={"to": "vip@example.com", "subject": "Urgent!"},
            priority=10,  # Higher priority (default is 5)
        )
        print(f"Enqueued priority job: {priority_job_id}")

        # --- Job with custom retry settings ---
        risky_job_id = client.enqueue(
            queue_name="data-processing",
            payload={"file": "large_dataset.csv"},
            priority=3,
            max_retries=5,  # Allow up to 5 retries on failure
        )
        print(f"Enqueued job with retries: {risky_job_id}")

        # --- Scheduled job (run in the future) ---
        future_time = "2025-12-31T23:59:59Z"
        scheduled_job_id = client.enqueue(
            queue_name="reminders",
            payload={"user_id": 123, "message": "Happy New Year!"},
            run_at=future_time,
        )
        print(f"Enqueued scheduled job: {scheduled_job_id}")

        # --- Batch enqueue ---
        batch_job_ids = client.enqueue_batch([
            {"queue_name": "batch-queue", "payload": {"task": "task1"}},
            {"queue_name": "batch-queue", "payload": {"task": "task2"}, "priority": 10},
            {"queue_name": "batch-queue", "payload": {"task": "task3"}, "max_retries": 5},
        ])
        print(f"Enqueued batch jobs: {len(batch_job_ids)} jobs")

        return [job_id, priority_job_id, risky_job_id, scheduled_job_id]


# =============================================================================
# EXAMPLE 4: Producer - Check Job Status
# =============================================================================


def example_check_status():
    """Check job status and get job details."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Check Job Status")
    print("=" * 60)

    with OpenQueue(BASE_URL, API_TOKEN) as client:
        # First, create a test job
        job_id = client.enqueue(
            queue_name="emails",
            payload={"to": "test@example.com", "subject": "Test"},
        )
        print(f"Created job: {job_id}")

        # --- Check status (quick) ---
        status = client.get_status(job_id)
        print(f"Job status: {status}")  # pending, processing, completed, failed, etc.

        # --- Get full job details ---
        job = client.get_job(job_id)
        print("\nJob Details:")
        print(f"  ID: {job.id}")
        print(f"  Queue: {job.queue_name}")
        print(f"  Status: {job.status}")
        print(f"  Priority: {job.priority}")
        print(f"  Payload: {job.payload}")
        print(f"  Created: {job.created_at}")

        if job.result:
            print(f"  Result: {job.result}")

        if job.error_text:
            print(f"  Error: {job.error_text}")

        return job_id


# =============================================================================
# EXAMPLE 5: Producer - List and Filter Jobs
# =============================================================================


def example_list_jobs():
    """List and filter jobs."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: List and Filter Jobs")
    print("=" * 60)

    with OpenQueue(BASE_URL, API_TOKEN) as client:
        # Create some test jobs first
        for i in range(3):
            client.enqueue(queue_name="test-queue", payload={"index": i})
        print("Created 3 test jobs")

        # --- List all pending jobs in a queue ---
        pending_jobs = client.list_jobs(
            queue_name="test-queue",
            status="pending",
            limit=10,
        )
        print(f"\nPending jobs in 'test-queue': {pending_jobs.total}")
        for job in pending_jobs.items:
            print(f"  - {job.id}: {job.payload}")

        # --- List all jobs (all statuses) ---
        all_jobs = client.list_jobs(
            queue_name="test-queue",
            limit=5,
        )
        print(f"\nAll jobs in 'test-queue': {all_jobs.total}")

        # --- List jobs with pagination ---
        page1 = client.list_jobs(queue_name="test-queue", limit=2, offset=0)
        page2 = client.list_jobs(queue_name="test-queue", limit=2, offset=2)
        print(f"\nPage 1: {len(page1.items)} jobs, Page 2: {len(page2.items)} jobs")


# =============================================================================
# EXAMPLE 6: Producer - Cancel Jobs
# =============================================================================


def example_cancel_job():
    """Cancel pending jobs."""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Cancel Jobs")
    print("=" * 60)

    with OpenQueue(BASE_URL, API_TOKEN) as client:
        # Create a test job
        job_id = client.enqueue(
            queue_name="test-queue",
            payload={"action": "test-cancel"},
        )
        print(f"Created job: {job_id}")

        # Check initial status
        status = client.get_status(job_id)
        print(f"Initial status: {status}")

        # Cancel the job (only works for pending jobs)
        try:
            client.cancel_job(job_id)
            print(f"Job {job_id} cancelled")

            # Verify cancellation
            status = client.get_status(job_id)
            print(f"Status after cancel: {status}")
        except OpenQueueError as e:
            print(f"Could not cancel job: {e}")


# =============================================================================
# EXAMPLE 7: Producer - Queue Statistics
# =============================================================================


def example_queue_stats():
    """Get queue statistics."""
    print("\n" + "=" * 60)
    print("EXAMPLE 7: Queue Statistics")
    print("=" * 60)

    with OpenQueue(BASE_URL, API_TOKEN) as client:
        # Create some test jobs
        client.enqueue(queue_name="stats-queue", payload={"test": 1})
        client.enqueue(queue_name="stats-queue", payload={"test": 2})

        # --- Get stats for all queues ---
        all_stats = client.get_queue_stats()
        print("All queue statistics:")
        for stats in all_stats:
            print(f"\n  Queue: {stats.queue_name}")
            print(f"    Pending: {stats.pending}")
            print(f"    Processing: {stats.processing}")
            print(f"    Completed: {stats.completed}")
            print(f"    Failed: {stats.failed}")
            print(f"    Cancelled: {stats.cancelled}")
            print(f"    Dead: {stats.dead}")


# =============================================================================
# EXAMPLE 8: Worker - Basic Job Processing
# =============================================================================


def example_basic_worker():
    """Basic worker pattern - lease, process, ack."""
    print("\n" + "=" * 60)
    print("EXAMPLE 8: Basic Worker")
    print("=" * 60)

    with OpenQueue(BASE_URL, API_TOKEN) as client:
        # Create a test job first
        job_id = client.enqueue(
            queue_name="worker-test",
            payload={"task": "process_order", "order_id": "12345"},
        )
        print(f"Created test job: {job_id}")

        # Worker configuration
        worker_id = "worker-001"
        queue_name = "worker-test"
        lease_seconds = 30

        # --- Lease a job ---
        leased = client.lease(
            queue_name=queue_name,
            worker_id=worker_id,
            lease_seconds=lease_seconds,
        )

        if leased is None:
            print("No jobs available")
            return

        job = leased.job
        print(f"Leased job: {job.id}")
        print(f"Payload: {job.payload}")
        print(f"Lease token: {leased.lease_token[:20]}...")
        print(f"Lease expires: {leased.lease_expires_at}")

        # --- Process the job ---
        try:
            # Your business logic here
            payload = job.payload or {}
            task = payload.get("task", "unknown")

            print(f"Processing task: {task}")
            time.sleep(1)  # Simulate work

            result = {"processed": True, "order_id": payload.get("order_id")}

            # --- Acknowledge successful completion ---
            client.ack(job.id, leased.lease_token, result=result)
            print(f"Job {job.id} acknowledged successfully")

        except Exception as e:
            # --- Handle failure ---
            client.nack(
                job.id,
                leased.lease_token,
                error=str(e),
                retry=True,  # Retry the job
            )
            print(f"Job {job.id} failed: {e}")


# =============================================================================
# EXAMPLE 9: Worker - Heartbeat for Long-Running Jobs
# =============================================================================


def example_worker_with_heartbeat():
    """Worker with heartbeat for long-running jobs."""
    print("\n" + "=" * 60)
    print("EXAMPLE 9: Worker with Heartbeat")
    print("=" * 60)

    with OpenQueue(BASE_URL, API_TOKEN) as client:
        # Create a long-running test job
        job_id = client.enqueue(
            queue_name="long-running",
            payload={"task": "backup_database"},
        )
        print(f"Created long-running job: {job_id}")

        worker_id = "worker-001"
        queue_name = "long-running"
        lease_seconds = 30

        # --- Lease the job ---
        leased = client.lease(
            queue_name=queue_name,
            worker_id=worker_id,
            lease_seconds=lease_seconds,
        )

        if leased is None:
            print("No jobs available")
            return

        job = leased.job
        print(f"Leased job: {job.id}")

        try:
            # --- Simulate long-running work with heartbeat ---
            for i in range(3):
                print(f"Working... ({i + 1}/3)")
                time.sleep(1)  # Do some work

                # --- Send heartbeat to extend lease ---
                client.heartbeat(job.id, leased.lease_token)
                print(f"Heartbeat sent for job {job.id}")

            # --- Job completed ---
            result = {"backup_completed": True, "size_gb": 50}
            client.ack(job.id, leased.lease_token, result=result)
            print(f"Job {job.id} completed with heartbeat")

        except Exception as e:
            client.nack(job.id, leased.lease_token, error=str(e), retry=True)
            print(f"Job {job.id} failed: {e}")


# =============================================================================
# EXAMPLE 10: Error Handling
# =============================================================================


def example_error_handling():
    """Proper error handling with the SDK."""
    print("\n" + "=" * 60)
    print("EXAMPLE 10: Error Handling")
    print("=" * 60)

    with OpenQueue(BASE_URL, API_TOKEN) as client:
        # --- Handle specific exceptions ---

        # ValidationError - Invalid parameters (e.g., invalid UUID format)
        try:
            client.get_status("non-existent-job-id")
        except ValidationError as e:
            print(f"Invalid job ID format: {e}")
        except (JobNotFoundError, OpenQueueError) as e:
            print(f"Job not found: {e}")

        # LeaseTokenError - Invalid or expired lease token
        try:
            # Try to ack with invalid token
            client.ack("some-job-id", "invalid-token")
        except (LeaseTokenError, OpenQueueError) as e:
            print(f"Lease token error: {e}")

        # RateLimitError - Too many requests
        try:
            client.get_status("some-job-id")
        except (RateLimitError, OpenQueueError) as e:
            print(f"Rate limited or error: {e}")

        # AuthenticationError - Invalid API token
        try:
            bad_client = OpenQueue(BASE_URL, "invalid-token")
            bad_client.get_status("some-job-id")
        except AuthenticationError as e:
            print(f"Authentication failed: {e}")

        # --- Generic error handling ---
        try:
            client.get_status("some-job-id")
        except OpenQueueError as e:
            print(f"OpenQueue error: {e}")


# =============================================================================
# EXAMPLE 11: Complete Producer-Consumer Workflow
# =============================================================================


def example_complete_workflow():
    """Complete producer-consumer workflow."""
    print("\n" + "=" * 60)
    print("EXAMPLE 11: Complete Workflow")
    print("=" * 60)

    with OpenQueue(BASE_URL, API_TOKEN) as client:
        # --- Producer: Enqueue multiple jobs ---
        print("\n--- Producer Phase ---")

        job_ids = []
        for i in range(5):
            job_id = client.enqueue(
                queue_name="orders",
                payload={
                    "order_id": f"ORD-{i + 1:04d}",
                    "amount": (i + 1) * 100,
                    "items": ["item1", "item2"],
                },
                priority=5 + i,  # Increasing priority
            )
            job_ids.append(job_id)

        print(f"Created {len(job_ids)} orders")

        # --- Check queue status ---
        stats = client.get_queue_stats()
        for s in stats:
            if s.queue_name == "orders":
                print(f"Orders queue: {s.pending} pending")

        # --- Worker: Process jobs ---
        print("\n--- Worker Phase ---")

        worker_id = "order-processor"
        processed = 0

        while processed < 3:  # Process 3 jobs for demo
            leased = client.lease(
                queue_name="orders",
                worker_id=worker_id,
                lease_seconds=30,
            )

            if leased is None:
                print("No more jobs")
                break

            job = leased.job
            payload = job.payload or {}

            print(f"Processing order: {payload.get('order_id')}")

            try:
                # Simulate processing
                time.sleep(0.5)

                result = {
                    "order_id": payload.get("order_id"),
                    "status": "completed",
                    "tracking_number": f"TRK-{job.id[:8]}",
                }

                client.ack(job.id, leased.lease_token, result=result)
                print(f"Order {payload.get('order_id')} completed")
                processed += 1

            except Exception as e:
                client.nack(job.id, leased.lease_token, error=str(e), retry=True)
                print(f"Order {payload.get('order_id')} failed: {e}")

        # --- Check final status ---
        print("\n--- Final Status ---")

        for job_id in job_ids[:3]:
            job = client.get_job(job_id)
            print(f"Job {job.id}: {job.status} - Result: {job.result}")

        remaining = client.list_jobs(queue_name="orders", status="pending")
        print(f"\nRemaining pending jobs: {remaining.total}")


# =============================================================================
# MAIN - Run All Examples
# =============================================================================

if __name__ == "__main__":
    print("OpenQueue SDK - Complete Usage Examples")
    print("=" * 60)

    # Run all examples
    example_basic_client()
    example_context_manager()
    example_producer()
    example_check_status()
    example_list_jobs()
    example_cancel_job()
    example_queue_stats()
    example_basic_worker()
    example_worker_with_heartbeat()
    example_error_handling()
    example_complete_workflow()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)
