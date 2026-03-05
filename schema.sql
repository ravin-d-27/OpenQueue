CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    queue_name TEXT NOT NULL,
    payload JSONB NOT NULL,

    -- Status lifecycle:
    -- pending -> processing -> completed
    -- pending -> cancelled
    -- processing -> failed -> (optional) pending (retry) OR dead (DLQ)
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

    -- Dead-letter queue (DLQ) fields
    dead_at TIMESTAMP,
    dead_reason TEXT,

    -- Attempts/lease metadata (lightweight; full attempts table can be added later)
    lease_lost_count INTEGER NOT NULL DEFAULT 0
);

-- Enforce valid statuses at the DB level
ALTER TABLE jobs
    ADD CONSTRAINT jobs_status_check
    CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled', 'dead'));

-- Basic sanity constraints
ALTER TABLE jobs
    ADD CONSTRAINT jobs_retry_count_non_negative CHECK (retry_count >= 0),
    ADD CONSTRAINT jobs_max_retries_non_negative CHECK (max_retries >= 0);

-- Critical indexes for performance

-- Lease hot path: find next eligible pending job quickly (global / pre-multi-tenant)
CREATE INDEX idx_jobs_pending_ready
    ON jobs(queue_name, status, run_at, priority DESC, created_at)
    WHERE status = 'pending';

-- Re-lease expired jobs (visibility timeout recovery)
CREATE INDEX idx_jobs_processing_expired
    ON jobs(queue_name, locked_until)
    WHERE status = 'processing';

-- Payload search (optional)
CREATE INDEX idx_jobs_payload_gin ON jobs USING GIN (payload);

-- Status filtering (optional)
CREATE INDEX idx_jobs_status ON jobs(status);



-- Users (tenants)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    api_token_hash TEXT NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMP
);

-- Jobs ownership (multi-tenancy)
ALTER TABLE jobs
    ADD COLUMN user_id UUID;

ALTER TABLE jobs
    ADD CONSTRAINT jobs_user_fk FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Backfill if you already have jobs (create a user first, then set this)
-- UPDATE jobs SET user_id = '<some-user-uuid>' WHERE user_id IS NULL;

ALTER TABLE jobs
    ALTER COLUMN user_id SET NOT NULL;

-- Helpful multi-tenant indexes

-- Producer/dashboard listing
CREATE INDEX idx_jobs_user_queue_status_created
    ON jobs(user_id, queue_name, status, created_at);

-- Worker lease hot path (pending ready)
CREATE INDEX idx_jobs_user_queue_pending_ready
    ON jobs(user_id, queue_name, run_at, priority DESC, created_at)
    WHERE status = 'pending';

-- Worker lease recovery (expired processing leases)
CREATE INDEX idx_jobs_user_queue_processing_expired
    ON jobs(user_id, queue_name, locked_until)
    WHERE status = 'processing';

-- DLQ listing per tenant
CREATE INDEX idx_jobs_user_queue_dead
    ON jobs(user_id, queue_name, dead_at)
    WHERE status = 'dead';

INSERT INTO users (email, api_token_hash, is_active)
VALUES ('admin@openqueue.local', 'a8000977a3ac8b4524c6ccd95a9935bc34b3be9fae30baaf15e5b103e293398a', TRUE)
ON CONFLICT (api_token_hash) DO NOTHING;
