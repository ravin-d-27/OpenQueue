from typing import Any, Dict, Optional

import asyncpg

from .database import db
from .models import JobStatus


async def create_job(
    queue_name: str, payload: Dict[str, Any], priority: int = 0, max_retries: int = 3
):
    async with db.get_pool() as pool:
        conn = await pool.acquire()
        try:
            result = await conn.fetchrow(
                """
                INSERT INTO jobs (queue_name, payload, priority, max_retries)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """,
                queue_name,
                payload,
                priority,
                max_retries,
            )
            return result["id"]
        finally:
            await pool.release(conn)


async def get_next_job(queue_name: str):
    async with db.get_pool() as pool:
        conn = await pool.acquire()
        try:
            row = await conn.fetchrow(
                """
                SELECT * FROM jobs
                WHERE queue_name = $1 AND status = 'pending'
                ORDER BY priority DESC, created_at ASC
                LIMIT 1 FOR UPDATE SKIP LOCKED
            """,
                queue_name,
            )
            if row:
                await conn.execute(
                    """
                    UPDATE jobs SET status = 'processing', updated_at = NOW()
                    WHERE id = $1
                """,
                    row["id"],
                )
            return dict(row) if row else None
        finally:
            await pool.release(conn)


async def update_job_result(
    job_id: str, result: Dict[str, Any] = None, error: str = None
):
    async with db.get_pool() as pool:
        status = "completed" if result is not None else "failed"
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE jobs
                SET status = $1, result = $2, error_text = $3, updated_at = NOW()
                WHERE id = $4
            """,
                status,
                result,
                error,
                job_id,
            )


async def get_job_status(job_id: str) -> Optional[str]:
    async with db.get_pool() as pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT status FROM jobs WHERE id = $1
                """,
                job_id,
            )
            return row["status"] if row else None
