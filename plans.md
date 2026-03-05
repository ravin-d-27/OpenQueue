# OpenQueue - Future Plans

This document outlines the roadmap for making OpenQueue a production-ready, useful job queue service for real-world users.

---

## Phase 1: Production Hardening (High Priority)

### 1.1 Distributed Rate Limiting & Quotas

- [ ] Implement Redis-backed or Postgres-backed rate limiting for multi-replica deployments
- [ ] Add per-tenant rate limits (RPS caps)
- [ ] Add payload size limits
- [ ] Add queue depth limits per tenant
- [ ] Add concurrent in-flight job limits per tenant/queue

**Why**: Current in-memory rate limiting only works for single-instance deployments.

### 1.2 API Key Management

- [ ] Support multiple API keys per user (`api_keys` table)
- [ ] Add `last_used_at` tracking per key
- [ ] Implement key rotation without downtime
- [ ] Add key naming/labeling for user convenience
- [ ] Support scoped keys (worker-only vs dashboard-only)

**Why**: Real production tenants need key rotation and multiple credentials.

### 1.3 Job Attempts / Audit Trail

- [ ] Create `job_attempts` table
- [ ] Record each lease/ack/nack event with timestamps
- [ ] Store worker_id, duration, error/result snapshots
- [ ] Expose attempt history via API

**Why**: Essential for debugging failures and building user-facing history.

### 1.4 API Versioning

- [ ] Deprecate `/jobs` → migrate to `/v1/jobs`
- [ ] Maintain backward compatibility during transition
- [ ] Document migration path

**Why**: Stabilize client contracts for production use.

---

## Phase 2: Observability & Debugging (High Priority)

### 2.1 Enhanced Logging

- [ ] Add structured logging (JSON format)
- [ ] Include job_id, user_id, worker_id in logs
- [ ] Add request/response logging for debugging

### 2.2 Request Tracing

- [ ] Add OpenTelemetry or similar distributed tracing
- [ ] Propagate trace context through job lifecycle

### 2.3 Improved Metrics

- [ ] Per-tenant queue depth metrics
- [ ] Retry rate and DLQ rate metrics
- [ ] Lease duration histograms
- [ ] Rate limit hit/miss metrics

### 2.4 Health & Readiness

- [ ] Add explicit DB ping for readiness checks
- [ ] Add migration version verification
- [ ] Add pool size metrics

---

## Phase 3: Developer Experience (Medium Priority)

### 3.1 SDKs / Client Libraries

- [ ] Python SDK (official)
- [ ] JavaScript/TypeScript SDK
- [ ] Go SDK

### 3.2 Webhooks

- [ ] Add webhook notifications for job completion/failure
- [ ] Support per-tenant webhook URLs
- [ ] Add retry logic for webhook delivery

### 3.3 Enhanced Dashboard API

- [ ] Add endpoint to get queue health summary
- [ ] Add endpoint for recent failures
- [ ] Add endpoint to requeue jobs from DLQ

### 3.4 CLI Tool

- [ ] CLI for managing jobs (enqueue, list, retry, cancel)
- [ ] Support for lease/ack workflow directly from CLI

---

## Phase 4: Reliability & Correctness (Medium Priority)

### 4.1 Comprehensive Test Suite

- [ ] Integration tests for all CRUD operations
- [ ] Concurrency tests (expand existing test)
- [ ] Lease expiry recovery tests
- [ ] Heartbeat tests
- [ ] Backoff timing tests
- [ ] DLQ transition tests

### 4.2 CI/CD Pipeline

- [ ] GitHub Actions workflow
- [ ] Run migrations on PR
- [ ] Run full test suite
- [ ] Lint and type checking

### 4.3 Chaos Engineering

- [ ] Test behavior under DB connection drops
- [ ] Test behavior under worker crashes
- [ ] Test lease expiry scenarios

---

## Phase 5: Operational Excellence (Lower Priority)

### 5.1 Connection Pool Tuning

- [ ] Make pool size configurable
- [ ] Add statement timeouts
- [ ] Add connection health checks

### 5.2 Retention Policies

- [ ] Configurable retention period (auto-delete old jobs)
- [ ] Archive completed jobs to cold storage (optional)
- [ ] DLQ auto-cleanup policy

### 5.3 Performance Optimization

- [ ] Analyze and optimize hot-path queries
- [ ] Add query performance metrics
- [ ] Benchmark under load

### 5.4 Multi-Region Support (Future)

- [ ] Consider read replicas for leasing
- [ ] Geo-routing for producers

---

## Phase 6: Ecosystem Integrations (Future)

### 6.1 Popular Framework Integrations

- [ ] Celery broker backend
- [ ] Django integration
- [ ] FastAPI integration helpers

### 6.2 Monitoring Integrations

- [ ] Datadog exporter
- [ ] CloudWatch exporter
- [ ] Grafana dashboard templates

---

## Priority Summary

| Priority | Items |
|----------|-------|
| **Must Have** | Distributed rate limiting, API keys, job attempts, API versioning |
| **Should Have** | Enhanced logging, tracing, comprehensive tests |
| **Nice to Have** | SDKs, webhooks, CLI, retention policies |

---

## Notes

- Focus on **Phase 1** items first — these are blockers for any real multi-tenant deployment
- Phase 2 improves debugging in production, which is critical for operator confidence
- Phase 3 can be parallelized once core is stable
- Consider community contributions for SDKs and integrations
