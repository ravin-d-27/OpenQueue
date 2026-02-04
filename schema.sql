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
