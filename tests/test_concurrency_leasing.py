from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import string
from typing import Set, Tuple

import asyncpg
import pytest


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _hmac_hash_for_configured_auth(token: str) -> str:
    """
    Mirror OpenQueue's token hashing behavior:

    - If OPENQUEUE_TOKEN_HMAC_SECRET is set: HMAC-SHA256(secret, token)
    - Else: SHA-256(token)

    This keeps the test compatible with the app's auth strategy.
    """
    secret = os.getenv("OPENQUEUE_TOKEN_HMAC_SECRET")
    if secret:
        import hmac

        return hmac.new(
            key=secret.encode("utf-8"),
            msg=token.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

    return _sha256_hex(token)


async def _ensure_schema(conn) -> None:
    """
    Create the minimal schema required for leasing tests.

    Note:
    - This test creates schema objects directly to keep it runnable against an empty DB.
    - If you migrate using Alembic in CI, this is still safe due to IF NOT EXISTS.
    """
    await conn.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT UNIQUE,
            api_token_hash TEXT NOT NULL UNIQUE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            last_seen_at TIMESTAMP
        );
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            queue_name TEXT NOT NULL,
            payload JSONB NOT NULL,

            status TEXT NOT NULL DEFAULT 'pending',
            priority INTEGER NOT NULL DEFAULT 0,

            retry_count INTEGER NOT NULL DEFAULT 0,
            max_retries INTEGER NOT NULL DEFAULT 3,

            run_at TIMESTAMP NOT NULL DEFAULT NOW(),

            locked_until TIMESTAMP,
            locked_by TEXT,
            lease_token UUID,

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            started_at TIMESTAMP,
            finished_at TIMESTAMP,

            result JSONB,
            error_text TEXT,

            dead_at TIMESTAMP,
            dead_reason TEXT,

            lease_lost_count INTEGER NOT NULL DEFAULT 0,

            CONSTRAINT jobs_status_check
              CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled', 'dead')),
            CONSTRAINT jobs_retry_count_non_negative CHECK (retry_count >= 0),
            CONSTRAINT jobs_max_retries_non_negative CHECK (max_retries >= 0)
        );
        """
    )

    await conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_jobs_user_queue_pending_ready
            ON jobs(user_id, queue_name, run_at, priority DESC, created_at)
            WHERE status = 'pending';
        """
    )
    await conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_jobs_user_queue_processing_expired
            ON jobs(user_id, queue_name, locked_until)
            WHERE status = 'processing';
        """
    )


async def _setup_test_user(conn) -> Tuple[str, str]:
    """
    Create a user and return (user_id, raw_token).
    """
    raw_token = "oq_test_" + "".join(
        random.choice(string.ascii_letters) for _ in range(24)
    )
    token_hash = _hmac_hash_for_configured_auth(raw_token)

    row = await conn.fetchrow(
        """
        INSERT INTO users (email, api_token_hash, is_active)
        VALUES ($1, $2, TRUE)
        RETURNING id
        """,
        f"{raw_token}@example.com",
        token_hash,
    )
    return str(row["id"]), raw_token


async def _enqueue_jobs(
    conn,
    *,
    user_id: str,
    queue_name: str,
    count: int,
    priority: int = 0,
) -> None:
    # Bulk insert for speed
    values = []
    for i in range(count):
        payload = {"i": i}
        values.append((user_id, queue_name, payload, priority))

    # asyncpg can require JSONB to be passed as a JSON string depending on codecs/config.
    # Use json.dumps(payload) to avoid "expected str, got dict" errors.
    #
    # Ensure the values tuple size matches the INSERT parameters (4 values):
    #   (user_id, queue_name, payload_json, priority)
    values = [(uid, qn, json.dumps(pl), pr) for (uid, qn, pl, pr) in values]

    await conn.executemany(
        """
        INSERT INTO jobs (user_id, queue_name, payload, priority)
        VALUES ($1, $2, $3::jsonb, $4)
        """,
        values,
    )


async def _lease_one(
    pool,
    *,
    user_id: str,
    queue_name: str,
    worker_id: str,
    lease_seconds: int = 30,
) -> str | None:
    """
    Lease one job using the same SQL semantics as OpenQueue's CRUD:

    - eligible if pending+run_at<=now OR processing+locked_until<now
    - order by priority desc, created_at asc
    - FOR UPDATE SKIP LOCKED
    - update status=processing, set lease token, locked_until, locked_by
    """
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
                    locked_until = NOW() + ($2 || ' seconds')::interval,
                    lease_token = gen_random_uuid(),
                    lease_lost_count = CASE
                        WHEN status = 'processing' AND locked_until IS NOT NULL AND locked_until < NOW()
                        THEN lease_lost_count + 1
                        ELSE lease_lost_count
                    END
                WHERE id = $3 AND user_id = $4
                RETURNING id
                """,
                worker_id,
                str(lease_seconds),
                row["id"],
                user_id,
            )

            return str(leased["id"]) if leased else None


@pytest.mark.asyncio
async def test_concurrent_leasing_no_duplicates() -> None:
    """
    Integration test: concurrent workers leasing jobs should never receive duplicates.

    Requirements:
    - DATABASE_URL must point to a running Postgres instance.
      (For CI, use Testcontainers or docker-compose to provide it.)

    What this test verifies:
    - With N jobs and M concurrent leasers, the set of leased job ids has:
        - no duplicates
        - size == N (all jobs were claimed exactly once)
    """
    database_url = os.getenv("DATABASE_URL")
    assert database_url, "DATABASE_URL must be set for integration tests"

    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=20)
    try:
        async with pool.acquire() as conn:
            await _ensure_schema(conn)

            # Clean slate (avoid cross-test contamination)
            await conn.execute("TRUNCATE TABLE jobs RESTART IDENTITY CASCADE;")
            await conn.execute("TRUNCATE TABLE users RESTART IDENTITY CASCADE;")

            user_id, _token = await _setup_test_user(conn)
            await _enqueue_jobs(
                conn, user_id=user_id, queue_name="default", count=100, priority=0
            )

        # Lease concurrently
        concurrency = 25
        tasks = []
        for i in range(concurrency):
            tasks.append(
                asyncio.create_task(
                    _lease_one(
                        pool,
                        user_id=user_id,
                        queue_name="default",
                        worker_id=f"worker-{i}",
                        lease_seconds=30,
                    )
                )
            )

        leased_ids: Set[str] = set()
        # We need to keep leasing until no jobs remain.
        # We'll repeatedly fire batches of concurrent lease attempts.
        while True:
            batch = await asyncio.gather(*tasks)
            for job_id in batch:
                if job_id is not None:
                    assert job_id not in leased_ids, (
                        f"Duplicate lease detected for job_id={job_id}"
                    )
                    leased_ids.add(job_id)

            # stop when we can no longer lease anything in a full batch
            if all(job_id is None for job_id in batch):
                break

            # reset tasks for next round
            tasks = []
            for i in range(concurrency):
                tasks.append(
                    asyncio.create_task(
                        _lease_one(
                            pool,
                            user_id=user_id,
                            queue_name="default",
                            worker_id=f"worker-{i}",
                            lease_seconds=30,
                        )
                    )
                )

        assert len(leased_ids) == 100, (
            f"Expected 100 unique leases, got {len(leased_ids)}"
        )

        # Verify DB state: all jobs should be processing, none pending
        async with pool.acquire() as conn:
            pending = await conn.fetchval(
                "SELECT COUNT(*) FROM jobs WHERE user_id = $1 AND queue_name = $2 AND status = 'pending'",
                user_id,
                "default",
            )
            processing = await conn.fetchval(
                "SELECT COUNT(*) FROM jobs WHERE user_id = $1 AND queue_name = $2 AND status = 'processing'",
                user_id,
                "default",
            )
            assert int(pending) == 0
            assert int(processing) == 100
    finally:
        await pool.close()
