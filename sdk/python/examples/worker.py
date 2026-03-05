"""
Example: Simple worker - lease, process, and ack jobs
"""

import time
from openqueue import OpenQueue

# Initialize client
client = OpenQueue(
    base_url="http://localhost:8000",
    api_token="oq_live_qXxA5liMxzRhz3uVTFYziaQSrw8tB05y2hU5O7VivyA",
)

# Worker configuration
WORKER_ID = "worker-1"
QUEUE_NAME = "default"
LEASE_SECONDS = 30

print(f"Worker {WORKER_ID} starting...")

while True:
    try:
        # Lease a job (returns None if queue is empty)
        leased = client.lease(
            queue_name=QUEUE_NAME,
            worker_id=WORKER_ID,
            lease_seconds=LEASE_SECONDS,
        )

        if leased is None:
            # No jobs available, wait before polling again
            print("No jobs available, waiting...")
            time.sleep(5)
            continue

        job = leased.job
        print(f"Leased job: {job.id}")
        print(f"Payload: {job.payload}")

        try:
            # === Your job processing logic here ===
            payload = job.payload or {}
            task = payload.get("task", "unknown")
            
            if task == "send_email":
                # Simulate sending email
                print("Sending email...")
                time.sleep(2)
                result = {"sent": True, "message_id": "msg-123"}
                
            elif task == "process_payment":
                # Simulate payment processing
                print("Processing payment...")
                time.sleep(5)
                result = {"processed": True, "transaction_id": "txn-456"}
                
            else:
                # Generic task
                print(f"Processing task: {task}")
                time.sleep(1)
                result = {"done": True}

            # Acknowledge successful completion
            client.ack(job.id, leased.lease_token, result=result)
            print(f"Job {job.id} completed successfully")

        except Exception as e:
            # Report failure - will retry if retries remain
            error_msg = str(e)
            client.nack(
                job.id,
                leased.lease_token,
                error=error_msg,
                retry=True,  # Set to False to move directly to DLQ
            )
            print(f"Job {job.id} failed: {error_msg}")

    except KeyboardInterrupt:
        print("Worker shutting down...")
        break
    except Exception as e:
        print(f"Worker error: {e}")
        time.sleep(5)

client.close()
