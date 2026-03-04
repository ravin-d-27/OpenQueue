from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ..database import db

router = APIRouter(tags=["Observability"])


@router.get(
    "/health",
    summary="Health check (liveness)",
    description="Liveness probe. Returns OK if the HTTP process is running.",
    response_model=dict,
)
async def health() -> dict:
    return {"status": "ok"}


@router.get(
    "/ready",
    summary="Readiness check (DB connectivity)",
    description=(
        "Readiness probe. Returns OK only if the service can reach the database.\n\n"
        "This endpoint intentionally does NOT require authentication so it can be used by "
        "orchestrators (Docker/Kubernetes) as a readiness probe."
    ),
    response_model=dict,
    responses={
        500: {
            "description": "Database not reachable",
            "content": {
                "application/json": {"example": {"detail": "Database not ready"}}
            },
        }
    },
)
async def ready() -> dict:
    try:
        async with db.get_pool() as pool:
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1;")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not ready",
        )
    return {"status": "ready"}


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Expose Prometheus metrics for OpenQueue.",
    response_class=Response,
)
async def metrics() -> Response:
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
