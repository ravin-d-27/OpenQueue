from __future__ import annotations

from fastapi import APIRouter

from ..deps import AuthUserDep, RateLimitQueueStatsDep
from ..services.jobs_service import queue_stats

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/queues",
    summary="Queue statistics",
    description="Returns per-queue counts by status for the authenticated user.",
    response_model=list[dict],
)
async def dashboard_queues_endpoint(
    user: AuthUserDep,
    _: RateLimitQueueStatsDep,
) -> list[dict]:
    return await queue_stats(user_id=user["id"])
