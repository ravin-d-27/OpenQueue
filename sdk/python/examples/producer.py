"""
Example: Simple producer - enqueue jobs
"""

from openqueue import OpenQueue

# Initialize client
client = OpenQueue(
    base_url="http://localhost:8000",
    api_token="oq_live_qXxA5liMxzRhz3uVTFYziaQSrw8tB05y2hU5O7VivyA",
)

# Enqueue a simple job
job_id = client.enqueue(
    queue_name="default",
    payload={"task": "send_email", "to": "user@example.com"},
)
print(f"Enqueued job: {job_id}")

# Enqueue with priority
priority_job_id = client.enqueue(
    queue_name="urgent",
    payload={"task": "process_payment", "order_id": "12345"},
    priority=10,
    max_retries=5,
)
print(f"Enqueued priority job: {priority_job_id}")

# Check status
print(f"Status: {client.get_status(job_id)}")

# Get full job details
job = client.get_job(job_id)
print(f"Job details: {job}")

# List jobs
jobs = client.list_jobs(queue_name="default", status="pending", limit=10)
print(f"Pending jobs: {jobs.total}")

# Get queue stats
stats = client.get_queue_stats()
for s in stats:
    print(f"Queue '{s.queue_name}': {s.pending} pending, {s.processing} processing")

client.close()
