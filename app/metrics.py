"""
OpenQueue Prometheus metrics.

This module defines counters/histograms for key queue operations.
It is intentionally lightweight and does not require an ORM.

Usage:
- Import and increment metrics in endpoints/CRUD.
- Expose /metrics via `prometheus_client.generate_latest()` in FastAPI.

Notes:
- Avoid putting high-cardinality labels on metrics (e.g. job_id, lease_token).
- queue_name and status can become high-cardinality in some setups; use sparingly.

Typing notes:
- Some editors/linters run with strict import resolution and may flag
  `prometheus_client` even when it's installed at runtime. To keep diagnostics
  quiet while staying correct, we use `TYPE_CHECKING` for type-only imports.
"""

from __future__ import annotations

from typing import Optional

from prometheus_client import Counter, Gauge, Histogram

# -------------------------
# Request-level metrics
# -------------------------

HTTP_REQUESTS_TOTAL = Counter(
    name="openqueue_http_requests_total",
    documentation="Total HTTP requests handled by OpenQueue.",
    labelnames=("method", "path", "status_code"),
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    name="openqueue_http_request_duration_seconds",
    documentation="HTTP request duration in seconds.",
    labelnames=("method", "path"),
    # Buckets tuned for typical API latencies (adjust as needed)
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

# -------------------------
# Queue operation metrics
# -------------------------

JOBS_ENQUEUED_TOTAL = Counter(
    name="openqueue_jobs_enqueued_total",
    documentation="Total jobs enqueued.",
    labelnames=("queue_name",),
)

JOBS_LEASED_TOTAL = Counter(
    name="openqueue_jobs_leased_total",
    documentation="Total jobs leased to workers.",
    labelnames=("queue_name",),
)

JOBS_LEASE_EMPTY_TOTAL = Counter(
    name="openqueue_jobs_lease_empty_total",
    documentation="Total lease attempts that returned no job.",
    labelnames=("queue_name",),
)

JOBS_ACKED_TOTAL = Counter(
    name="openqueue_jobs_acked_total",
    documentation="Total jobs acknowledged as completed by workers.",
    labelnames=("queue_name",),
)

JOBS_NACKED_TOTAL = Counter(
    name="openqueue_jobs_nacked_total",
    documentation="Total jobs negatively acknowledged by workers.",
    labelnames=("queue_name", "outcome"),
)

JOBS_CANCELLED_TOTAL = Counter(
    name="openqueue_jobs_cancelled_total",
    documentation="Total jobs cancelled by producers.",
    labelnames=("queue_name",),
)

JOBS_MOVED_TO_DLQ_TOTAL = Counter(
    name="openqueue_jobs_moved_to_dlq_total",
    documentation="Total jobs moved to dead-letter queue.",
    labelnames=("queue_name", "reason"),
)

LEASE_EXPIRED_RECOVERED_TOTAL = Counter(
    name="openqueue_lease_expired_recovered_total",
    documentation="Total times an expired lease was recovered and re-leased.",
    labelnames=("queue_name",),
)

JOB_PROCESSING_DURATION_SECONDS = Histogram(
    name="openqueue_job_processing_duration_seconds",
    documentation="Job processing duration in seconds (started_at -> finished_at).",
    labelnames=("queue_name", "final_status"),
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300, 600),
)

# -------------------------
# Gauges (optional / best-effort)
# -------------------------

DB_POOL_IN_USE = Gauge(
    name="openqueue_db_pool_in_use",
    documentation="Approximate number of DB connections currently acquired from the pool.",
)

DB_POOL_SIZE = Gauge(
    name="openqueue_db_pool_size",
    documentation="Approximate DB pool size.",
)


def observe_processing_duration(
    *,
    queue_name: str,
    final_status: str,
    duration_seconds: Optional[float],
) -> None:
    """
    Convenience helper to observe processing duration safely.

    This function avoids raising on None/negative durations and keeps
    the call-sites clean.
    """
    if duration_seconds is None:
        return
    if duration_seconds < 0:
        return

    JOB_PROCESSING_DURATION_SECONDS.labels(
        queue_name=queue_name,
        final_status=final_status,
    ).observe(float(duration_seconds))
