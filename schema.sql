CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    queue_name TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- pending, processing, completed, failed
    priority INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    result JSONB,
    error_text TEXT
);

-- Critical indexes for performance
CREATE INDEX idx_jobs_pending ON jobs(queue_name, status, priority, created_at)
WHERE status = 'pending';
CREATE INDEX idx_jobs_payload_gin ON jobs USING GIN (payload);
CREATE INDEX idx_jobs_status ON jobs(status);



-- Alter TABLE to add new columns for tracking
-- Users (tenants)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    api_token_hash TEXT NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMP
);

-- Jobs ownership + leasing fields
ALTER TABLE jobs
    ADD COLUMN user_id UUID,
    ADD COLUMN run_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ADD COLUMN locked_until TIMESTAMP,
    ADD COLUMN locked_by TEXT,
    ADD COLUMN lease_token UUID,
    ADD COLUMN started_at TIMESTAMP,
    ADD COLUMN finished_at TIMESTAMP;

ALTER TABLE jobs
    ADD CONSTRAINT jobs_user_fk FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Backfill if you already have jobs (create a user first, then set this)
-- UPDATE jobs SET user_id = '<some-user-uuid>' WHERE user_id IS NULL;

ALTER TABLE jobs
    ALTER COLUMN user_id SET NOT NULL;

-- Helpful indexes
CREATE INDEX idx_jobs_user_queue_status_created
    ON jobs(user_id, queue_name, status, created_at);

CREATE INDEX idx_jobs_user_queue_pending_ready
    ON jobs(user_id, queue_name, priority DESC, created_at)
    WHERE status = 'pending';

-- Optional: speed up re-leasing timed-out jobs later
CREATE INDEX idx_jobs_processing_timed_out
    ON jobs(user_id, queue_name, locked_until)
    WHERE status = 'processing';

INSERT INTO users (email, api_token_hash, is_active)
VALUES ('admin@openqueue.local', 'a8000977a3ac8b4524c6ccd95a9935bc34b3be9fae30baaf15e5b103e293398a', TRUE)
ON CONFLICT (api_token_hash) DO NOTHING;
