# OpenQueue

A PostgreSQL-backed job queue service with HTTP API. Built for developers who want durability, inspectability, and simplicity.

![Python Version](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
[![PyPI](https://img.shields.io/pypi/v/openqueue-pg)](https://pypi.org/project/openqueue-pg/)
[![GitHub](https://img.shields.io/github/stars/ravin-d-27/OpenQueue)](https://github.com/ravin-d-27/OpenQueue)

## Why OpenQueue?

| Use Case | Why OpenQueue |
|----------|---------------|
| Need durable job storage | Jobs are rows in Postgres - query, debug, audit |
| Already using Postgres | No additional infrastructure |
| Building a SaaS | Built-in multi-tenancy with API tokens |
| Compliance needs | Full job history in relational DB |
| Simpler operations | One DB to manage |

## Quick Start

### Docker Compose (Recommended)

```bash
docker compose up --build
```

This starts:
- `openqueue-db` - PostgreSQL
- `openqueue-api` - FastAPI server (port 8000)
- `openqueue-dashboard` - Web dashboard (port 3000)

### Dashboard

Access the dashboard at: **http://localhost:3000**

Features:
- Terminal-style dark interface
- Real-time queue stats with auto-refresh (30s)
- Job listing with filtering
- Job detail view
- Settings for API configuration
- Local storage caching for offline resilience

### Configuration

Default API token (development only):
```
Bearer token: oq_live_qXxA5liMxzRhz3uVTFYziaQSrw8tB05y2hU5O7VivyA
```

Use it:
```bash
curl -H "Authorization: Bearer oq_live_qXxA5liMxzRhz3uVTFYziaQSrw8tB05y2hU5O7VivyA" \
  http://localhost:8000/dashboard/queues
```

## Core Concepts

### Producer - Enqueue Jobs

```python
from openqueue import OpenQueue

client = OpenQueue("http://localhost:8000", "your-token")

# Simple job
job_id = client.enqueue(
    queue_name="emails",
    payload={"to": "user@example.com", "subject": "Hello"}
)

# Scheduled job (run later)
job_id = client.enqueue(
    queue_name="reminders",
    payload={"message": "Reminder!"},
    run_at="2026-01-01T09:00:00Z"
)

# Batch enqueue
job_ids = client.enqueue_batch([
    {"queue_name": "emails", "payload": {"to": "a@b.com"}},
    {"queue_name": "emails", "payload": {"to": "c@d.com"}, "priority": 10},
])
```

### Worker - Process Jobs

```python
from openqueue import OpenQueue

client = OpenQueue("http://localhost:8000", "your-token")

while True:
    leased = client.lease(queue_name="emails", worker_id="worker-1")
    
    if leased:
        try:
            # Process the job
            payload = leased.job.payload
            print(f"Processing: {payload}")
            
            # Success
            client.ack(leased.job.id, leased.lease_token, result={"done": True})
        except Exception as e:
            # Failure - retry
            client.nack(leased.job.id, leased.lease_token, error=str(e))
```

## Architecture
Refer to the below image:
![Architecture Diagram](system-design/Architecture_diagram.png)

## Features

- **Job Priorities** - Higher priority jobs are processed first
- **Visibility Timeout** - Auto-recovery from worker crashes
- **Heartbeat** - Long-running jobs stay leased
- **Retry with Backoff** - Exponential backoff prevents retry storms
- **Dead Letter Queue** - Failed jobs isolated for inspection
- **Batch Operations** - Enqueue multiple jobs efficiently
- **Scheduled Jobs** - Delay job execution with `run_at`

## API Endpoints

### Producer
- `POST /jobs` - Enqueue job
- `GET /jobs/{id}` - Get job status  
- `GET /jobs` - List jobs
- `POST /jobs/batch` - Batch enqueue
- `POST /jobs/{id}/cancel` - Cancel pending job

### Worker
- `POST /queues/{name}/lease` - Lease next job
- `POST /jobs/{id}/ack` - Acknowledge success
- `POST /jobs/{id}/nack` - Report failure
- `POST /jobs/{id}/heartbeat` - Extend lease

### Dashboard
- `GET /dashboard/queues` - Queue statistics

## MCP Server

OpenQueue provides an MCP (Model Context Protocol) server for AI integrations. This allows AI assistants to interact with your job queue.

### Setup

```bash
# Install dependencies
pip install -r mcp/requirements.txt

# Run the MCP server
python mcp/openqueue_mcp.py
```

The server runs on port 8080 by default (configurable via `PORT` env var).

### Available Tools

| Tool | Description |
|------|-------------|
| `enqueue_job` | Enqueue a single job |
| `enqueue_job_batch` | Enqueue multiple jobs |
| `get_job_status` | Get status of a job |
| `get_job_details` | Get full details of a job |
| `list_jobs` | List jobs with filtering |
| `cancel_job` | Cancel a pending job |
| `lease_job` | Lease a job for processing |
| `ack_job` | Mark job as completed |
| `nack_job` | Mark job as failed |
| `heartbeat` | Extend job lease |
| `get_queue_stats` | Get queue statistics |

### Authentication

Pass your OpenQueue API token via the `Authorization` header:

```
Authorization: Bearer <your-token>
```

Or set the `OPENQUEUE_TOKEN` environment variable.

### Example Usage

```python
from fastmcp import Client

async with Client("http://localhost:8080/mcp", auth="your-token") as client:
    result = await client.call_tool("enqueue_job", {
        "queue_name": "emails",
        "payload": {"to": "user@example.com"},
    })
```

## Documentation

- [Concept.md](Concept.md) - Technical deep-dive for contributors
- [BEGINNER_GUIDE.md](BEGINNER_GUIDE.md) - Architecture walkthrough
- [system-design/OpenQueue-SystemDesign.excalidraw](system-design/OpenQueue-SystemDesign.excalidraw) - Architecture diagram (import in excalidraw.io)

## License

MIT
