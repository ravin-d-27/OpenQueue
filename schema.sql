-- ============================================================================
-- OpenQueue Database Schema
-- PostgreSQL-backed job queue service
-- ============================================================================

-- ============================================================================
-- Users Table (Tenants)
-- ============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    api_token_hash TEXT NOT NULL UNIQUE,  -- SHA-256 hash of API token
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMP
);

-- ============================================================================
-- Jobs Table (Queue Items)
-- ============================================================================
CREATE TABLE jobs (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    queue_name TEXT NOT NULL,

    -- Payload
    payload JSONB NOT NULL,

    -- Status lifecycle:
    -- pending -> processing -> completed
    -- pending -> cancelled
    -- processing -> failed -> (optional) pending (retry) OR dead (DLQ)
    status TEXT NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 0,

    -- Retry configuration
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

    -- Dead-letter queue (DLQ) fields
    dead_at TIMESTAMP,
    dead_reason TEXT,

    -- Lease metadata
    lease_lost_count INTEGER NOT NULL DEFAULT 0
);

-- ============================================================================
-- Constraints
-- ============================================================================

-- Enforce valid statuses at the DB level
ALTER TABLE jobs
    ADD CONSTRAINT jobs_status_check
    CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled', 'dead'));

-- Retry bounds must be non-negative
ALTER TABLE jobs
    ADD CONSTRAINT jobs_retry_count_non_negative CHECK (retry_count >= 0),
    ADD CONSTRAINT jobs_max_retries_non_negative CHECK (max_retries >= 0);

-- ============================================================================
-- Indexes (Hot Paths)
-- ============================================================================

-- Payload search (optional - for JSON querying)
CREATE INDEX idx_jobs_payload_gin ON jobs USING GIN (payload);

-- Status filtering (optional)
CREATE INDEX idx_jobs_status ON jobs(status);

-- --------------------------------------------------------------------------
-- Multi-tenant Indexes
-- --------------------------------------------------------------------------

-- Producer/dashboard listing: filter by user, queue, status, created
CREATE INDEX idx_jobs_user_queue_status_created
    ON jobs(user_id, queue_name, status, created_at);

-- Worker lease hot path: find next eligible pending job
CREATE INDEX idx_jobs_user_queue_pending_ready
    ON jobs(user_id, queue_name, run_at, priority DESC, created_at)
    WHERE status = 'pending';

-- Worker lease recovery: re-lease expired processing jobs
CREATE INDEX idx_jobs_user_queue_processing_expired
    ON jobs(user_id, queue_name, locked_until)
    WHERE status = 'processing';

-- DLQ listing: find dead jobs per tenant
CREATE INDEX idx_jobs_user_queue_dead
    ON jobs(user_id, queue_name, dead_at)
    WHERE status = 'dead';

-- ============================================================================
-- Default User (Development)
-- ============================================================================
-- Token: oq_live_qXxA5liMxzRhz3uVTFYziaQSrw8tB05y2hU5O7VivyA
-- SHA256: a8000977a3ac8b4524c6ccd95a9935bc34b3be9fae30baaf15e5b103e293398a
INSERT INTO users (email, api_token_hash, is_active)
VALUES ('admin@openqueue.local', 'a8000977a3ac8b4524c6ccd95a9935bc34b3be9fae30baaf15e5b103e293398a', TRUE)
ON CONFLICT (api_token_hash) DO NOTHING;
