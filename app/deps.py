from __future__ import annotations

"""
Shared FastAPI dependencies and helpers.

Goal:
- Keep endpoint functions thin and consistent.
- Centralize cross-cutting concerns:
  - Authentication (current user)
  - Rate limiting (per-user, per-action)
  - Request ID access (for logging/tracing)
  - Common error shapes

Notes:
- This project intentionally keeps the queue hot path in raw SQL.
- The rate limiter is currently in-memory (per-process). In multi-replica
  deployments you should replace/enhance it with gateway or distributed limiting.
"""

from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status

from .auth import CurrentUser, get_current_user
from .rate_limit import DEFAULT_LIMITS, RateLimiter, RateLimitExceeded

# -------------------------
# Core dependencies
# -------------------------

AuthUserDep = Annotated[CurrentUser, Depends(get_current_user)]

# Single in-memory limiter instance. This is fine for:
# - development
# - single-instance deployments
# For horizontally-scaled deployments, use a shared/distributed limiter.
_rate_limiter = RateLimiter(default_limits=DEFAULT_LIMITS)


def get_request_id(request: Request) -> Optional[str]:
    """
    Read request id from request.state. Set by RequestIdMiddleware.
    """
    return getattr(request.state, "request_id", None)


def get_rate_limit_principal(user: Optional[CurrentUser], request: Request) -> str:
    """
    Compute a stable principal key for rate limiting.

    Preference order:
    1) user["id"] (multi-tenant stable identifier)
    2) X-Request-ID (fallback; not ideal but avoids empty keys)
    3) "unknown"

    We intentionally do not use raw API tokens as principal keys.
    """
    if user and user.get("id"):
        return str(user["id"])
    rid = get_request_id(request)
    return rid or "unknown"


def rate_limit(
    *,
    action: str,
    tokens: float = 1.0,
):
    """
    Dependency factory for rate limiting.

    Usage:
        @router.get(...)
        async def handler(..., _=Depends(rate_limit(action="list_jobs"))):
            ...

    This keeps auth and rate limiting out of the endpoint signature/Docs while still
    enforcing limits consistently.
    """

    async def _dep(
        request: Request,
        user: AuthUserDep,
    ) -> None:
        principal = get_rate_limit_principal(user, request)
        try:
            _rate_limiter.consume(principal_key=principal, action=action, tokens=tokens)
        except RateLimitExceeded as e:
            # Use Retry-After to make clients behave well under load.
            retry_after = str(int(max(1.0, e.retry_after_seconds)))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": retry_after},
            )

    return _dep


# Convenience named dependencies for readability
RateLimitEnqueueDep = Annotated[None, Depends(rate_limit(action="enqueue"))]
RateLimitLeaseDep = Annotated[None, Depends(rate_limit(action="lease"))]
RateLimitAckDep = Annotated[None, Depends(rate_limit(action="ack"))]
RateLimitNackDep = Annotated[None, Depends(rate_limit(action="nack"))]
RateLimitHeartbeatDep = Annotated[None, Depends(rate_limit(action="heartbeat"))]
RateLimitListJobsDep = Annotated[None, Depends(rate_limit(action="list_jobs"))]
RateLimitQueueStatsDep = Annotated[None, Depends(rate_limit(action="queue_stats"))]
