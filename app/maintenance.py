"""
OpenQueue maintenance utilities.

This module contains database maintenance helpers intended to run periodically,
either:

1) As a background task inside the API process (simple deployments), or
2) As a separate "maintenance" container/cronjob (recommended for production),
   so heavy cleanup does not impact API latency.

Design goals:
- Keep logic SQL-first (no ORM required)
- Provide safe, idempotent operations
- Use conservative defaults

What belongs here:
- Lease reaping (optional): reset/requeue jobs with expired leases
  NOTE: OpenQueue already supports expired lease recovery at lease-time.
  Reaping is still useful to keep the system tidy and to apply policies
  even when traffic is low.
- Retention cleanup: delete/compact old completed/cancelled/failed jobs
- DLQ housekeeping (optional): archive or delete dead jobs after TTL

Important:
- These functions assume the schema includes:
  - jobs.locked_until, jobs.status, jobs.updated_at, jobs.finished_at, jobs.run_at
  - jobs.user_id, jobs.queue_name
  - jobs.dead_at, jobs.dead_reason (DLQ)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .database import db

logger = logging.getLogger("openqueue.maintenance")


@dataclass(frozen=True)
class MaintenanceConfig:
    """
    Configuration for maintenance operations.

    All durations are in seconds.
    """

    # How often to run periodic maintenance loop
    interval_seconds: int = 30

    # Lease reaper: consider "processing" jobs with locked_until < now() - grace as expired
    lease_expiry_grace_seconds: int = 0

    # When reaping an expired lease, decide how to transition:
    # - "pending": requeue job (status -> pending)
    # - "failed": fail job (status -> failed)
    # - "dead": move job to DLQ
    expired_lease_action: str = "pending"

    # Retention policies (delete old rows)
    delete_completed_after_seconds: Optional[int] = 7 * 24 * 3600
    delete_cancelled_after_seconds: Optional[int] = 7 * 24 * 3600
    delete_failed_after_seconds: Optional[int] = 14 * 24 * 3600
    delete_dead_after_seconds: Optional[int] = None  # keep DLQ by default

    # Limit deletes per run to reduce DB load
    delete_batch_size: int = 2_000


async def reap_expired_leases(
    *,
    grace_seconds: int = 0,
    action: str = "pending",
    batch_size: int = 2_000,
) -> int:
    """
    Reap expired leases.

    This is a best-effort policy hook. The core queue path already allows
    re-leasing expired jobs, but reaping helps keep processing queues clean.

    Parameters:
    - grace_seconds: extra time after locked_until before reaping
    - action:
        - "pending": set status back to pending and clear lease fields
        - "failed": set status to failed and clear lease fields
        - "dead": set status to dead, set dead_at/dead_reason, clear lease fields
    - batch_size: number of rows to update per run

    Returns:
    - number of jobs updated
    """
    grace_seconds = max(0, int(grace_seconds))
    batch_size = max(1, min(int(batch_size), 20_000))
    action = (action or "").strip().lower()

    if action not in {"pending", "failed", "dead"}:
        raise ValueError("action must be one of: pending, failed, dead")

    async with db.get_pool() as pool:
        async with pool.acquire() as conn:
            if action == "pending":
                sql = """
                WITH picked AS (
                    SELECT id
                    FROM jobs
                    WHERE status = 'processing'
                      AND locked_until IS NOT NULL
                      AND locked_until < (NOW() - ($1::text || ' seconds')::interval)
                    ORDER BY locked_until ASC
                    LIMIT $2
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE jobs
                SET status = 'pending',
                    updated_at = NOW(),
                    locked_until = NULL,
                    locked_by = NULL,
                    lease_token = NULL
                WHERE id IN (SELECT id FROM picked)
                RETURNING id;
                """
                rows = await conn.fetch(sql, grace_seconds, batch_size)
                return len(rows)

            if action == "failed":
                sql = """
                WITH picked AS (
                    SELECT id
                    FROM jobs
                    WHERE status = 'processing'
                      AND locked_until IS NOT NULL
                      AND locked_until < (NOW() - ($1::text || ' seconds')::interval)
                    ORDER BY locked_until ASC
                    LIMIT $2
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE jobs
                SET status = 'failed',
                    error_text = COALESCE(error_text, 'lease_expired'),
                    updated_at = NOW(),
                    finished_at = COALESCE(finished_at, NOW()),
                    locked_until = NULL,
                    locked_by = NULL,
                    lease_token = NULL
                WHERE id IN (SELECT id FROM picked)
                RETURNING id;
                """
                rows = await conn.fetch(sql, grace_seconds, batch_size)
                return len(rows)

            # action == "dead"
            sql = """
            WITH picked AS (
                SELECT id
                FROM jobs
                WHERE status = 'processing'
                  AND locked_until IS NOT NULL
                  AND locked_until < (NOW() - ($1::text || ' seconds')::interval)
                ORDER BY locked_until ASC
                LIMIT $2
                FOR UPDATE SKIP LOCKED
            )
            UPDATE jobs
            SET status = 'dead',
                error_text = COALESCE(error_text, 'lease_expired'),
                dead_reason = COALESCE(dead_reason, 'lease_expired'),
                dead_at = COALESCE(dead_at, NOW()),
                updated_at = NOW(),
                finished_at = COALESCE(finished_at, NOW()),
                locked_until = NULL,
                locked_by = NULL,
                lease_token = NULL
            WHERE id IN (SELECT id FROM picked)
            RETURNING id;
            """
            rows = await conn.fetch(sql, grace_seconds, batch_size)
            return len(rows)


async def delete_old_jobs(
    *,
    status: str,
    older_than_seconds: int,
    batch_size: int = 2_000,
) -> int:
    """
    Delete jobs of a specific status older than a given age.

    Uses finished_at when available, otherwise falls back to updated_at.

    Returns number of rows deleted (best-effort; limited by batch_size).
    """
    status = (status or "").strip().lower()
    older_than_seconds = max(0, int(older_than_seconds))
    batch_size = max(1, min(int(batch_size), 50_000))

    if status not in {"completed", "cancelled", "failed", "dead"}:
        raise ValueError("status must be one of: completed, cancelled, failed, dead")

    async with db.get_pool() as pool:
        async with pool.acquire() as conn:
            sql = """
            WITH picked AS (
                SELECT id
                FROM jobs
                WHERE status = $1
                  AND COALESCE(finished_at, updated_at) < (NOW() - ($2::text || ' seconds')::interval)
                ORDER BY COALESCE(finished_at, updated_at) ASC
                LIMIT $3
                FOR UPDATE SKIP LOCKED
            )
            DELETE FROM jobs
            WHERE id IN (SELECT id FROM picked)
            RETURNING id;
            """
            rows = await conn.fetch(sql, status, older_than_seconds, batch_size)
            return len(rows)


async def run_maintenance_once(config: MaintenanceConfig) -> Dict[str, Any]:
    """
    Run one maintenance iteration.

    Returns a dict with counts for each operation.
    """
    results: Dict[str, Any] = {}

    # 1) Lease reaping (optional but useful)
    try:
        reaped = await reap_expired_leases(
            grace_seconds=config.lease_expiry_grace_seconds,
            action=config.expired_lease_action,
            batch_size=config.delete_batch_size,
        )
        results["reaped_expired_leases"] = reaped
    except Exception as e:
        logger.exception("maintenance.reap_expired_leases_failed")
        results["reaped_expired_leases_error"] = str(e)

    # 2) Retention cleanup
    async def _maybe_delete(key: str, status: str, ttl: Optional[int]) -> None:
        if ttl is None:
            results[key] = 0
            return
        try:
            deleted = await delete_old_jobs(
                status=status,
                older_than_seconds=ttl,
                batch_size=config.delete_batch_size,
            )
            results[key] = deleted
        except Exception as e:
            logger.exception(
                "maintenance.delete_old_jobs_failed", extra={"status": status}
            )
            results[f"{key}_error"] = str(e)

    await _maybe_delete(
        "deleted_completed", "completed", config.delete_completed_after_seconds
    )
    await _maybe_delete(
        "deleted_cancelled", "cancelled", config.delete_cancelled_after_seconds
    )
    await _maybe_delete("deleted_failed", "failed", config.delete_failed_after_seconds)
    await _maybe_delete("deleted_dead", "dead", config.delete_dead_after_seconds)

    return results


async def maintenance_loop(
    *,
    config: MaintenanceConfig,
    stop_event: Optional[asyncio.Event] = None,
) -> None:
    """
    Periodic maintenance loop.

    This function is designed to run forever until stop_event is set, e.g.
    from a FastAPI lifespan event.

    Usage example (conceptual):
        stop = asyncio.Event()
        task = asyncio.create_task(maintenance_loop(config=MaintenanceConfig(), stop_event=stop))
        ...
        stop.set()
        await task
    """
    interval = max(1, int(config.interval_seconds))
    stop_event = stop_event or asyncio.Event()

    logger.info("maintenance.loop_started", extra={"interval_seconds": interval})

    while not stop_event.is_set():
        start = asyncio.get_event_loop().time()
        try:
            res = await run_maintenance_once(config)
            logger.info("maintenance.iteration_done", extra={"results": res})
        except Exception:
            logger.exception("maintenance.iteration_failed")

        elapsed = asyncio.get_event_loop().time() - start
        sleep_for = max(0.0, interval - elapsed)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=sleep_for)
        except asyncio.TimeoutError:
            # normal loop tick
            pass

    logger.info("maintenance.loop_stopped")
