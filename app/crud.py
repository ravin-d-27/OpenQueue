import json
import uuid
from typing import Any, Dict, List, Optional, Tuple

from .database import db


def _to_iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    # asyncpg returns datetime objects; make them JSON-friendly
    try:
        return dt.isoformat()
    except Exception:
        return str(dt)


def _maybe_parse_json(value: Any) -> Any:
    """
    asyncpg + jsonb can sometimes return JSON as a Python dict, but depending on
    codecs/config it may come back as a JSON string. Normalize to dict/list.
    """
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def _row_to_job_dict(row: Any) -> Dict[str, Any]:
    """
    Convert an asyncpg.Record (or mapping) into an API-friendly dict.
    """
    return {
        "id": str(row["id"]),
        "queue_name": row["queue_name"],
        "status": row["status"],
        "priority": row["priority"],
        "payload": _maybe_parse_json(row["payload"]),
        "result": _maybe_parse_json(row.get("result")),
        "error_text": row.get("error_text"),
        "retry_count": row.get("retry_count"),
        "max_retries": row.get("max_retries"),
        "created_at": _to_iso(row.get("created_at")),
        "updated_at": _to_iso(row.get("updated_at")),
        "started_at": _to_iso(row.get("started_at")),
        "finished_at": _to_iso(row.get("finished_at")),
        "run_at": _to_iso(row.get("run_at")),
        "locked_until": _to_iso(row.get("locked_until")),
        "locked_by": row.get("locked_by"),
        "lease_token": str(row["lease_token"]) if row.get("lease_token") else None,
    }


async def create_job(
    user_id: str,
    queue_name: str,
    payload: Dict[str, Any],
    priority: int = 0,
    max_retries: int = 3,
) -> str:
    async with db.get_pool() as pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO jobs (user_id, queue_name, payload, priority, max_retries)
                VALUES ($1, $2, $3::jsonb, $4, $5)
                RETURNING id
                """,
                user_id,
                queue_name,
                json.dumps(payload),
                priority,
                max_retries,
            )
            return str(row["id"])


async def get_job_status(user_id: str, job_id: str) -> Optional[str]:
    async with db.get_pool() as pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT status
                FROM jobs
                WHERE id = $1 AND user_id = $2
                """,
                job_id,
                user_id,
            )
            return row["status"] if row else None


async def get_job(user_id: str, job_id: str) -> Optional[Dict[str, Any]]:
    async with db.get_pool() as pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT *
                FROM jobs
                WHERE id = $1 AND user_id = $2
                """,
                job_id,
                user_id,
            )
            return _row_to_job_dict(row) if row else None


async def list_jobs(
    user_id: str,
    queue_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Returns (items, total).
    """
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))

    clauses: List[str] = ["user_id = $1"]
    args: List[Any] = [user_id]
    idx = 2

    if queue_name:
        clauses.append(f"queue_name = ${idx}")
        args.append(queue_name)
        idx += 1

    if status:
        clauses.append(f"status = ${idx}")
        args.append(status)
        idx += 1

    where_sql = " AND ".join(clauses)

    async with db.get_pool() as pool:
        async with pool.acquire() as conn:
            total = await conn.fetchval(
                f"SELECT COUNT(*) FROM jobs WHERE {where_sql}",
                *args,
            )

            rows = await conn.fetch(
                f"""
                SELECT *
                FROM jobs
                WHERE {where_sql}
                ORDER BY created_at DESC
                LIMIT ${idx} OFFSET ${idx + 1}
                """,
                *args,
                limit,
                offset,
            )

            return ([_row_to_job_dict(r) for r in rows], int(total or 0))


async def get_queue_stats(user_id: str) -> List[Dict[str, Any]]:
    async with db.get_pool() as pool:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    queue_name,
                    COUNT(*) FILTER (WHERE status = 'pending')       AS pending,
                    COUNT(*) FILTER (WHERE status = 'processing')    AS processing,
                    COUNT(*) FILTER (WHERE status = 'completed')     AS completed,
                    COUNT(*) FILTER (WHERE status = 'failed')        AS failed,
                    COUNT(*) FILTER (WHERE status = 'cancelled')     AS cancelled,
                    COUNT(*) FILTER (WHERE status = 'dead')          AS dead,
                    COUNT(*)                                         AS total,
                    MIN(created_at) FILTER (WHERE status = 'pending') AS oldest_pending_created_at
                FROM jobs
                WHERE user_id = $1
                GROUP BY queue_name
                ORDER BY queue_name ASC
                """,
                user_id,
            )

            return [
                {
                    "queue_name": r["queue_name"],
                    "pending": int(r["pending"] or 0),
                    "processing": int(r["processing"] or 0),
                    "completed": int(r["completed"] or 0),
                    "failed": int(r["failed"] or 0),
                    "cancelled": int(r["cancelled"] or 0),
                    "dead": int(r["dead"] or 0),
                    "total": int(r["total"] or 0),
                    "oldest_pending_created_at": _to_iso(
                        r["oldest_pending_created_at"]
                    ),
                }
                for r in rows
            ]


async def lease_next_job(
    user_id: str,
    queue_name: str,
    worker_id: str,
    lease_seconds: int = 30,
) -> Optional[Dict[str, Any]]:
    """
    Atomically pick the next pending job and mark it processing with a lease token.

    Requires schema columns:
      - run_at, locked_until, locked_by, lease_token, started_at
    """
    lease_seconds = max(1, min(int(lease_seconds), 3600))

    async with db.get_pool() as pool:
        async with pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    SELECT id
                    FROM jobs
                    WHERE user_id = $1
                      AND queue_name = $2
                      AND status = 'pending'
                      AND COALESCE(run_at, NOW()) <= NOW()
                    ORDER BY priority DESC, created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                    """,
                    user_id,
                    queue_name,
                )
                if not row:
                    return None

                leased = await conn.fetchrow(
                    """
                    UPDATE jobs
                    SET status = 'processing',
                        updated_at = NOW(),
                        started_at = COALESCE(started_at, NOW()),
                        locked_by = $1,
                        locked_until = NOW() + ($2::text || ' seconds')::interval,
                        lease_token = gen_random_uuid()
                    WHERE id = $3 AND user_id = $4
                    RETURNING *
                    """,
                    worker_id,
                    lease_seconds,
                    row["id"],
                    user_id,
                )

                return _row_to_job_dict(leased) if leased else None


async def ack_job(
    user_id: str,
    job_id: str,
    lease_token: str,
    result: Optional[Dict[str, Any]] = None,
) -> bool:
    # Guard against invalid UUID strings so we return False instead of 500'ing
    try:
        uuid.UUID(str(lease_token))
    except Exception:
        return False
    """
    Complete a leased job (idempotent-ish: only succeeds if lease_token matches).
    Returns True if updated, False otherwise.
    """
    async with db.get_pool() as pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE jobs
                SET status = 'completed',
                    result = $1::jsonb,
                    error_text = NULL,
                    updated_at = NOW(),
                    finished_at = NOW(),
                    locked_until = NULL,
                    locked_by = NULL,
                    lease_token = NULL
                WHERE id = $2
                  AND user_id = $3
                  AND status = 'processing'
                  AND lease_token = $4::uuid
                RETURNING id
                """,
                json.dumps(result) if result is not None else None,
                job_id,
                user_id,
                lease_token,
            )
            return bool(row)


async def nack_job(
    user_id: str,
    job_id: str,
    lease_token: str,
    error: str,
    retry: bool = True,
) -> bool:
    # Guard against invalid UUID strings so we return False instead of 500'ing
    try:
        uuid.UUID(str(lease_token))
    except Exception:
        return False
    """
    Mark a leased job as failed, optionally requeueing if retries remain.

    Note: This is a basic implementation. Backoff/delayed retry can be added later
    by updating run_at.
    """
    async with db.get_pool() as pool:
        async with pool.acquire() as conn:
            async with conn.transaction():
                current = await conn.fetchrow(
                    """
                    SELECT id, retry_count, max_retries
                    FROM jobs
                    WHERE id = $1
                      AND user_id = $2
                      AND status = 'processing'
                      AND lease_token = $3::uuid
                    FOR UPDATE
                    """,
                    job_id,
                    user_id,
                    lease_token,
                )
                if not current:
                    return False

                retry_count = int(current["retry_count"] or 0)
                max_retries = int(current["max_retries"] or 0)

                can_retry = bool(retry) and retry_count < max_retries
                new_status = "pending" if can_retry else "failed"

                await conn.execute(
                    """
                    UPDATE jobs
                    SET status = $1,
                        retry_count = retry_count + 1,
                        error_text = $2,
                        updated_at = NOW(),
                        finished_at = CASE WHEN $1 = 'failed' THEN NOW() ELSE finished_at END,
                        locked_until = NULL,
                        locked_by = NULL,
                        lease_token = NULL
                    WHERE id = $3 AND user_id = $4
                    """,
                    new_status,
                    error,
                    job_id,
                    user_id,
                )

                return True


async def cancel_job(user_id: str, job_id: str) -> bool:
    """
    Cancel a job if it's still pending.
    Returns True if cancelled, False if not found or not pending.
    """
    async with db.get_pool() as pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE jobs
                SET status = 'cancelled',
                    updated_at = NOW(),
                    finished_at = NOW()
                WHERE id = $1 AND user_id = $2 AND status = 'pending'
                RETURNING id
                """,
                job_id,
                user_id,
            )
            return bool(row)
