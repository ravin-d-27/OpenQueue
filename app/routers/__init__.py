"""
OpenQueue router package.

This package groups FastAPI routers by functional area:
- jobs: producer/client-facing APIs
- workers: worker/lease APIs (BYOW)
- dashboard: read-only stats APIs
- observability: health/readiness/metrics APIs

The app factory imports routers from here to keep app wiring clean.
"""

from __future__ import annotations

__all__ = [
    "jobs",
    "workers",
    "dashboard",
    "observability",
]

from . import dashboard, jobs, observability, workers
