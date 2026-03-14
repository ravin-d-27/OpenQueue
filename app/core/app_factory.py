from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..middleware import (
    PrometheusHttpMetricsMiddleware,
    RequestIdMiddleware,
    StructuredLoggingMiddleware,
)
from ..routers import dashboard, jobs, observability, workers
from ..settings import get_settings


def create_app(*, title: str = "OpenQueue", version: str = "0.0.1") -> FastAPI:
    """
    Build and configure the FastAPI application.

    Responsibilities:
    - Configure OpenAPI metadata
    - Register middleware (request ids, structured logs, Prometheus metrics)
    - Include API routers

    Notes:
    - This keeps `fastapi_app.py` minimal and makes testing easier.
    - Router modules are responsible for their own paths and tags.
    """
    tags_metadata = [
        {
            "name": "Jobs (Producer)",
            "description": "Client-facing endpoints to enqueue jobs and inspect/cancel them.",
        },
        {
            "name": "Workers (BYOW)",
            "description": "Worker endpoints to lease jobs and ack/nack/heartbeat results.",
        },
        {
            "name": "Dashboard",
            "description": "Read-only endpoints for queue statistics and listings.",
        },
        {
            "name": "Observability",
            "description": "Operational endpoints such as health/readiness and Prometheus metrics.",
        },
    ]

    app = FastAPI(
        title=title,
        version=version,
        summary="Hosted, Postgres-backed job queue service",
        description=(
            "OpenQueue is a hosted queue service intended to replace Redis queues for many workloads. "
            "Clients enqueue jobs, and workers lease jobs for processing using a lease token.\n\n"
            "## Authentication\n"
            "Most endpoints require an API token via `Authorization: Bearer <token>`.\n\n"
            "## Worker semantics\n"
            "- `lease`: atomically claims the next eligible job in a queue.\n"
            "- `ack`: completes a leased job.\n"
            "- `nack`: fails a leased job, optionally requeueing with backoff.\n"
            "- `heartbeat`: extends a lease for long-running jobs.\n"
        ),
        openapi_tags=tags_metadata,
    )

    # CORS middleware
    settings = get_settings()
    cors_origins = [o.strip() for o in settings.cors_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Middleware
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(StructuredLoggingMiddleware)
    app.add_middleware(PrometheusHttpMetricsMiddleware)

    # Routers
    app.include_router(observability.router)
    app.include_router(jobs.router)
    app.include_router(workers.router)
    app.include_router(dashboard.router)

    # Basic logger defaults (kept conservative; apps can override)
    logging.getLogger("openqueue.http").setLevel(logging.INFO)
    logging.getLogger("openqueue.maintenance").setLevel(logging.INFO)

    return app
