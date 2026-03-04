"""Initial schema: users and jobs tables with constraints and indexes.

Revision ID: 0001_init_schema
Revises: None
Create Date: 2026-03-04

This migration creates:
- users table (API token auth)
- jobs table (multi-tenant queue with leasing, scheduling, retries, DLQ)
- constraints and indexes required for core operations

Notes:
- Requires the pgcrypto extension for gen_random_uuid().
- Uses explicit SQL to keep parity with the project's SQL-first approach.
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_init_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure UUID generator exists (works on Postgres, including many hosted providers).
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

    # Users (tenants)
    op.execute(
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

    # Jobs (queue items)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            queue_name TEXT NOT NULL,

            payload JSONB NOT NULL,

            -- Status lifecycle:
            -- pending -> processing -> completed
            -- pending -> cancelled
            -- processing -> pending (retry) OR dead (DLQ)
            status TEXT NOT NULL DEFAULT 'pending',

            priority INTEGER NOT NULL DEFAULT 0,

            retry_count INTEGER NOT NULL DEFAULT 0,
            max_retries INTEGER NOT NULL DEFAULT 3,

            -- Scheduling: job should not be leased before run_at
            run_at TIMESTAMP NOT NULL DEFAULT NOW(),

            -- Leasing / visibility-timeout support
            locked_until TIMESTAMP,
            locked_by TEXT,
            lease_token UUID,

            -- Timing metadata
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            started_at TIMESTAMP,
            finished_at TIMESTAMP,

            -- Output
            result JSONB,
            error_text TEXT,

            -- Dead-letter queue (DLQ)
            dead_at TIMESTAMP,
            dead_reason TEXT,

            -- Lease recovery tracking
            lease_lost_count INTEGER NOT NULL DEFAULT 0,

            -- Constraints
            CONSTRAINT jobs_status_check
              CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled', 'dead')),
            CONSTRAINT jobs_retry_count_non_negative CHECK (retry_count >= 0),
            CONSTRAINT jobs_max_retries_non_negative CHECK (max_retries >= 0)
        );
        """
    )

    # Indexes for producer/dashboard listing
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_jobs_user_queue_status_created
            ON jobs(user_id, queue_name, status, created_at);
        """
    )

    # Lease hot path (pending + ready)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_jobs_user_queue_pending_ready
            ON jobs(user_id, queue_name, run_at, priority DESC, created_at)
            WHERE status = 'pending';
        """
    )

    # Lease recovery (expired processing leases)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_jobs_user_queue_processing_expired
            ON jobs(user_id, queue_name, locked_until)
            WHERE status = 'processing';
        """
    )

    # DLQ listing per tenant
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_jobs_user_queue_dead
            ON jobs(user_id, queue_name, dead_at)
            WHERE status = 'dead';
        """
    )

    # Optional indexes (useful at scale)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_jobs_status
            ON jobs(status);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_jobs_payload_gin
            ON jobs USING GIN (payload);
        """
    )


def downgrade() -> None:
    # Drop in dependency order
    op.execute("DROP TABLE IF EXISTS jobs;")
    op.execute("DROP TABLE IF EXISTS users;")
    # Keep extension installed (safe and commonly shared). Uncomment if you want strict rollback:
    # op.execute('DROP EXTENSION IF EXISTS "pgcrypto";')
