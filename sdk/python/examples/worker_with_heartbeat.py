"""
Example: Worker with heartbeat for long-running jobs
"""

import time
import threading
from openqueue import OpenQueue

# Initialize client
client = OpenQueue(
    base_url="http://localhost:8000",
    api_token="oq_live_qXxA5liMxzRhz3uVTFYziaQSrw8tB05y2hU5O7VivyA",
)

WORKER_ID = "long-running-worker"
QUEUE_NAME = "heavy-jobs"
LEASE_SECONDS = 30


def heartbeat_loop(job_id: str, lease_token: str, interval: int = 10):
    """Send heartbeats to keep the lease alive."""
    while True:
        time.sleep(interval)
        try:
            success = client.heartbeat(job_id, lease_token, lease_seconds=LEASE_SECONDS)
            if success:
                print(f"Heartbeat sent for job {job_id}")
            else:
                print(f"Failed to send heartbeat (job may no longer be leased)")
                break
        except Exception as e:
            print(f"Heartbeat error: {e}")
            break


print(f"Worker {WORKER_ID} starting...")

while True:
    try:
        leased = client.lease(
            queue_name=QUEUE_NAME,
            worker_id=WORKER_ID,
            lease_seconds=LEASE_SECONDS,
        )

        if leased is None:
            print("No jobs available, waiting...")
            time.sleep(5)
            continue

        job = leased.job
        print(f"Leased job: {job.id}")

        # Start heartbeat in background thread
        heartbeat_thread = threading.Thread(
            target=heartbeat_loop,
            args=(job.id, leased.lease_token, 10),
            daemon=True,
        )
        heartbeat_thread.start()

        try:
            # Simulate long-running task
            print(f"Processing long-running job (will take ~60 seconds)...")
            time.sleep(60)

            # Complete the job
            client.ack(job.id, leased.lease_token, result={"status": "done"})
            print(f"Job {job.id} completed")

        except Exception as e:
            client.nack(job.id, leased.lease_token, error=str(e))
            print(f"Job {job.id} failed: {e}")

    except KeyboardInterrupt:
        print("Worker shutting down...")
        break

client.close()
