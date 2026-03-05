import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from .database import db


def _compute_retry_delay_seconds(retry_count: int) -> int:
    """
    Exponential backoff (seconds) with a cap.
    - retry_count is the current retry_count BEFORE increment.
    - returns delay seconds for the NEXT retry.
    """
    # 1, 2, 4, 8, ... seconds up to 300 seconds cap
    base = 2 ** max(0, int(retry_count))
    return min(base, 300)


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
    run_at: Optional[str] = None,
) -> str:
    run_at_dt = None
    if run_at:
        run_at_dt = datetime.fromisoformat(run_at.replace("Z", "+00:00")).replace(tzinfo=None)

    async with db.get_pool() as pool:
        async with pool.acquire() as conn:
            if run_at_dt:
                row = await conn.fetchrow(
                    """
                    INSERT INTO jobs (user_id, queue_name, payload, priority, max_retries, run_at)
                    VALUES ($1, $2, $3::jsonb, $4, $5, $6)
                    RETURNING id
                    """,
                    user_id,
                    queue_name,
                    json.dumps(payload),
                    priority,
                    max_retries,
                    run_at_dt,
                )
            else:
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


async def create_jobs_batch(
    user_id: str,
    jobs: List[Dict[str, Any]],
) -> List[str]:
    """
    Insert multiple jobs in a single database call for efficiency.
    """
    if not jobs:
        return []

    async with db.get_pool() as pool:
        async with pool.acquire() as conn:
            job_rows = []
            for job in jobs:
                if hasattr(job, "model_dump"):
                    job_dict = job.model_dump()
                else:
                    job_dict = job

                run_at_str = job_dict.get("run_at")
                run_at_dt = None
                if run_at_str:
                    run_at_dt = datetime.fromisoformat(run_at_str.replace("Z", "+00:00")).replace(tzinfo=None)

                if run_at_dt:
                    row = await conn.fetchrow(
                        """
                        INSERT INTO jobs (user_id, queue_name, payload, priority, max_retries, run_at)
                        VALUES ($1, $2, $3::jsonb, $4, $5, $6)
                        RETURNING id
                        """,
                        user_id,
                        job_dict["queue_name"],
                        json.dumps(job_dict["payload"]),
                        job_dict.get("priority", 0),
                        job_dict.get("max_retries", 3),
                        run_at_dt,
                    )
                else:
                    row = await conn.fetchrow(
                        """
                        INSERT INTO jobs (user_id, queue_name, payload, priority, max_retries)
                        VALUES ($1, $2, $3::jsonb, $4, $5)
                        RETURNING id
                        """,
                        user_id,
                        job_dict["queue_name"],
                        json.dumps(job_dict["payload"]),
                        job_dict.get("priority", 0),
                        job_dict.get("max_retries", 3),
                    )
                job_rows.append(str(row["id"]))

            return job_rows


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
    Atomically lease the next eligible job for a queue.

    Eligibility rules:
    - pending jobs where run_at <= NOW()
    - processing jobs where locked_until < NOW() (expired lease / visibility timeout recovery)

    Notes:
    - This provides "at-least-once" processing semantics. If a worker continues
      processing after its lease expires, the job may be processed more than once.
    - A re-leased job receives a new lease_token; stale workers will fail ack/nack
      with a token mismatch.
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
                      AND (
                        (status = 'pending' AND COALESCE(run_at, NOW()) <= NOW())
                        OR
                        (status = 'processing' AND locked_until IS NOT NULL AND locked_until < NOW())
                      )
                    ORDER BY
                      priority DESC,
                      created_at ASC
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
                        locked_until = NOW() + (($2)::text || ' seconds')::interval,
                        lease_token = gen_random_uuid(),
                        lease_lost_count = CASE
                            WHEN status = 'processing' AND locked_until IS NOT NULL AND locked_until < NOW()
                            THEN lease_lost_count + 1
                            ELSE lease_lost_count
                        END
                    WHERE id = $3 AND user_id = $4
                    RETURNING *
                    """,
                    worker_id,
                    str(lease_seconds),
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
                backoff_seconds = _compute_retry_delay_seconds(retry_count)

                if can_retry:
                    await conn.execute(
                        """
                        UPDATE jobs
                        SET status = 'pending',
                            retry_count = retry_count + 1,
                            error_text = $1,
                            run_at = NOW() + (($2)::text || ' seconds')::interval,
                            updated_at = NOW(),
                            locked_until = NULL,
                            locked_by = NULL,
                            lease_token = NULL
                        WHERE id = $3 AND user_id = $4
                        """,
                        error,
                        str(backoff_seconds),
                        job_id,
                        user_id,
                    )
                else:
                    await conn.execute(
                        """
                        UPDATE jobs
                        SET status = 'dead',
                            error_text = $1,
                            dead_reason = $2,
                            dead_at = NOW(),
                            updated_at = NOW(),
                            finished_at = NOW(),
                            locked_until = NULL,
                            locked_by = NULL,
                            lease_token = NULL
                        WHERE id = $3 AND user_id = $4
                        """,
                        error,
                        "max_retries_exhausted"
                        if retry_count >= max_retries
                        else "retry_disabled",
                        job_id,
                        user_id,
                    )

                return True


async def heartbeat_job(
    user_id: str,
    job_id: str,
    lease_token: str,
    lease_seconds: int = 30,
) -> bool:
    """
    Extend a job lease for long-running processing.
    Only succeeds if the job is currently processing and the lease_token matches.
    """
    lease_seconds = max(1, min(int(lease_seconds), 3600))

    # Guard against invalid UUID strings so we return False instead of 500'ing
    try:
        uuid.UUID(str(lease_token))
    except Exception:
        return False

    async with db.get_pool() as pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE jobs
                SET locked_until = NOW() + (($1)::text || ' seconds')::interval,
                    updated_at = NOW()
                WHERE id = $2
                  AND user_id = $3
                  AND status = 'processing'
                  AND lease_token = $4::uuid
                RETURNING id
                """,
                str(lease_seconds),
                job_id,
                user_id,
                lease_token,
            )
            return bool(row)


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
