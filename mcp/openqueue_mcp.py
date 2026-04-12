import os
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request
from openqueue import OpenQueue

mcp = FastMCP(name="OpenQueue")


def _get_bearer_token_from_request() -> Optional[str]:
    """
    Read Authorization: Bearer <token> from the incoming MCP HTTP request.
    Returns None if request/header is missing or malformed.
    """
    req = get_http_request()
    if req is None:
        return None

    auth_header = req.headers.get("authorization")
    if not auth_header:
        return None

    parts = auth_header.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1].strip()
    return token or None


def get_client() -> OpenQueue:
    """
    Create a per-request OpenQueue client.

    Priority:
        Bearer token from incoming request Authorization header
    """
    base_url = os.environ.get(
        "OPENQUEUE_BASE_URL", "https://open-queue-ivory.vercel.app"
    )
    token = _get_bearer_token_from_request()

    if not token:
        raise ValueError(
            "Missing OpenQueue token. Send Authorization: Bearer <token> "
            "or set OPENQUEUE_TOKEN."
        )

    return OpenQueue(base_url, token)


@mcp.tool
def enqueue_job(
    queue_name: str,
    payload: dict,
    priority: int = 0,
    max_retries: int = 3,
    run_at: Optional[str] = None,
) -> str:
    client = get_client()
    return client.enqueue(
        queue_name=queue_name,
        payload=payload,
        priority=priority,
        max_retries=max_retries,
        run_at=run_at,
    )


@mcp.tool
def enqueue_job_batch(jobs: List[Dict[str, Any]]) -> List[str]:
    client = get_client()
    return client.enqueue_batch(jobs)


@mcp.tool
def get_job_status(job_id: str) -> str:
    client = get_client()
    return client.get_status(job_id)


@mcp.tool
def get_job_details(job_id: str) -> Dict[str, Any]:
    client = get_client()
    data = client.get_job(job_id)
    return {
        "id": data.id,
        "queue_name": data.queue_name,
        "status": data.status,
        "priority": data.priority,
        "payload": data.payload,
        "result": data.result,
        "error_text": data.error_text,
        "retry_count": data.retry_count,
        "max_retries": data.max_retries,
        "created_at": str(data.created_at),
        "updated_at": str(data.updated_at),
        "started_at": str(data.started_at),
        "finished_at": str(data.finished_at),
    }


@mcp.tool
def list_jobs(
    queue_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    client = get_client()
    data = client.list_jobs(
        queue_name=queue_name,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [
            {
                "id": job.id,
                "queue_name": job.queue_name,
                "status": job.status,
                "priority": job.priority,
                "payload": job.payload,
            }
            for job in data.items
        ],
        "total": data.total,
        "limit": data.limit,
        "offset": data.offset,
    }


@mcp.tool
def cancel_job(job_id: str) -> bool:
    client = get_client()
    return client.cancel_job(job_id)


@mcp.tool
def lease_job(
    queue_name: str,
    worker_id: str,
    lease_seconds: int = 30,
) -> Optional[Dict[str, Any]]:
    client = get_client()
    leased = client.lease(queue_name, worker_id, lease_seconds)
    if leased is None:
        return None

    return {
        "lease_token": leased.lease_token,
        "job": {
            "id": leased.job.id,
            "queue_name": leased.job.queue_name,
            "payload": leased.job.payload,
            "priority": leased.job.priority,
            "retry_count": leased.job.retry_count,
            "max_retries": leased.job.max_retries,
        },
    }


@mcp.tool
def ack_job(
    job_id: str, lease_token: str, result: Optional[Dict[str, Any]] = None
) -> bool:
    client = get_client()
    return client.ack(job_id, lease_token, result)


@mcp.tool
def nack_job(job_id: str, lease_token: str, error: str, retry: bool = True) -> bool:
    client = get_client()
    return client.nack(job_id, lease_token, error, retry)


@mcp.tool
def heartbeat(job_id: str, lease_token: str, lease_seconds: int = 30) -> bool:
    client = get_client()
    return client.heartbeat(job_id, lease_token, lease_seconds)


@mcp.tool
def get_queue_stats() -> List[Dict[str, Any]]:
    client = get_client()
    stats = client.get_queue_stats()
    return [
        {
            "queue_name": s.queue_name,
            "pending": s.pending,
            "processing": s.processing,
            "completed": s.completed,
            "failed": s.failed,
        }
        for s in stats
    ]


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    mcp.run(transport="http", host="0.0.0.0", port=port)
