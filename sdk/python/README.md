# OpenQueue Python SDK

A Python client for [OpenQueue](https://github.com/ravin-d-27/openqueue), a PostgreSQL-backed job queue service.

## Installation

```bash
pip install openqueue
```

## Quick Start

### As a Producer

```python
from openqueue import OpenQueue

client = OpenQueue("http://localhost:8000", "your-api-token")

# Enqueue a job
job_id = client.enqueue(
    queue_name="emails",
    payload={"to": "user@example.com", "subject": "Hello"},
    priority=5,
)
print(f"Enqueued job: {job_id}")

# Check status
status = client.get_status(job_id)
print(f"Job status: {status}")

# List jobs
jobs = client.list_jobs(queue_name="emails", status="pending")
print(f"Pending jobs: {jobs.total}")
```

### As a Worker

```python
from openqueue import OpenQueue

client = OpenQueue("http://localhost:8000", "your-api-token")

while True:
    # Lease a job (blocks until available or returns None)
    leased = client.lease("emails", worker_id="worker-1", lease_seconds=30)
    
    if leased:
        try:
            # Process the job
            print(f"Processing job: {leased.job.id}")
            print(f"Payload: {leased.job.payload}")
            
            # Do your work here...
            result = {"processed": True, "records": 100}
            
            # Acknowledge completion
            client.ack(leased.job.id, leased.lease_token, result=result)
            print("Job completed successfully")
            
        except Exception as e:
            # Report failure (will retry if retries remain)
            client.nack(leased.job.id, leased.lease_token, error=str(e))
            print(f"Job failed: {e}")
    else:
        # No job available, wait before trying again
        time.sleep(1)
```

### With Context Manager

```python
from openqueue import OpenQueue

with OpenQueue("http://localhost:8000", "your-api-token") as client:
    job_id = client.enqueue("queue", {"task": "do_something"})
    # Client automatically closed when exiting context
```

## API Reference

### Producer Methods

| Method | Description |
|--------|-------------|
| `enqueue(queue_name, payload, priority, max_retries)` | Create a new job |
| `get_status(job_id)` | Get job status |
| `get_job(job_id)` | Get full job details |
| `list_jobs(queue_name, status, limit, offset)` | List jobs with filters |
| `cancel_job(job_id)` | Cancel a pending job |

### Worker Methods

| Method | Description |
|--------|-------------|
| `lease(queue_name, worker_id, lease_seconds)` | Lease next available job |
| `ack(job_id, lease_token, result)` | Acknowledge successful completion |
| `nack(job_id, lease_token, error, retry)` | Report failure |
| `heartbeat(job_id, lease_token, lease_seconds)` | Extend job lease |

### Dashboard Methods

| Method | Description |
|--------|-------------|
| `get_queue_stats()` | Get queue statistics |

## Error Handling

```python
from openqueue import (
    OpenQueue,
    JobNotFoundError,
    LeaseTokenError,
    RateLimitError,
    AuthenticationError,
)

try:
    client.enqueue("queue", {"task": "test"})
except AuthenticationError:
    print("Invalid API token")
except RateLimitError:
    print("Rate limited, try again later")
except JobNotFoundError:
    print("Job not found")
except LeaseTokenError:
    print("Invalid lease token")
```

## Configuration

```python
client = OpenQueue(
    base_url="http://localhost:8000",
    api_token="your-api-token",
    timeout=30.0,        # Request timeout in seconds
    max_retries=3,      # Retry attempts for transient errors
)
```

## License

MIT
