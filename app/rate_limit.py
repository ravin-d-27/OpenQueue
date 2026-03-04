"""
In-memory rate limiting and payload guardrails for OpenQueue.

This module is intentionally lightweight and dependency-free:
- No Redis required
- No DB writes required
- Suitable for single-instance deployments and development
- In multi-replica deployments, limits are enforced per replica (not globally)

Design goals:
- Simple token-bucket rate limiter per (token_hash, action)
- Fixed window counters are easy but bursty; token bucket is smoother
- Guardrails for max request body size (best-effort at app layer)

Integration approach:
- Use `RateLimiter` as a FastAPI dependency (recommended) or call from middleware.
- Use `enforce_json_size_guardrail` in endpoints before accepting large payloads.

NOTE:
For a hosted production service with multiple API replicas, you will likely replace
(or complement) this with a distributed rate limiter (Redis, Postgres advisory locks,
or a dedicated gateway rate limiter).
"""

from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class RateLimit:
    """
    Token bucket rate limit.

    - rate_per_sec: steady-state refill rate in tokens/sec
    - burst: bucket capacity (max tokens)
    """

    rate_per_sec: float
    burst: int


class RateLimitExceeded(Exception):
    """
    Raised when a rate limit is exceeded.
    """

    def __init__(self, *, action: str, retry_after_seconds: float):
        super().__init__(f"Rate limit exceeded for action='{action}'")
        self.action = action
        self.retry_after_seconds = retry_after_seconds


class PayloadTooLarge(Exception):
    """
    Raised when a payload exceeds configured size guardrails.
    """

    def __init__(self, *, max_bytes: int, actual_bytes: int):
        super().__init__(f"Payload too large (max={max_bytes}B actual={actual_bytes}B)")
        self.max_bytes = max_bytes
        self.actual_bytes = actual_bytes


class _TokenBucket:
    """
    Internal token bucket state.

    tokens: current tokens
    updated_at: last refill timestamp (monotonic)
    """

    __slots__ = ("tokens", "updated_at")

    def __init__(self, tokens: float, updated_at: float):
        self.tokens = tokens
        self.updated_at = updated_at


class RateLimiter:
    """
    In-memory token bucket rate limiter.

    Keys:
      (principal_key, action) -> token bucket

    Where principal_key should be stable and low cardinality:
    - API token hash (preferred)
    - user_id
    - IP address (not recommended for authenticated APIs)

    Thread safety:
    - Uses a single lock to protect the buckets dict.
    - Suitable for typical FastAPI single-process + async workloads.
    """

    def __init__(
        self,
        *,
        default_limits: Dict[str, RateLimit],
        max_entries: int = 50_000,
        gc_interval_seconds: int = 60,
        idle_ttl_seconds: int = 15 * 60,
    ):
        self._default_limits = dict(default_limits)
        self._max_entries = int(max_entries)
        self._gc_interval_seconds = int(gc_interval_seconds)
        self._idle_ttl_seconds = int(idle_ttl_seconds)

        self._lock = threading.Lock()
        self._buckets: Dict[Tuple[str, str], _TokenBucket] = {}
        self._last_gc = time.monotonic()

    def get_limit(self, action: str) -> Optional[RateLimit]:
        return self._default_limits.get(action)

    @staticmethod
    def _now() -> float:
        return time.monotonic()

    def _maybe_gc(self, now: float) -> None:
        if now - self._last_gc < self._gc_interval_seconds:
            return

        # Garbage collect idle buckets to prevent unbounded memory growth.
        cutoff = now - self._idle_ttl_seconds
        # O(n) scan; OK for moderate sizes. For huge scale, replace with LRU cache.
        keys_to_delete = []
        for key, bucket in self._buckets.items():
            if bucket.updated_at < cutoff:
                keys_to_delete.append(key)

        for key in keys_to_delete:
            self._buckets.pop(key, None)

        # Hard cap safety: if still too large, drop oldest-ish by updated_at.
        if len(self._buckets) > self._max_entries:
            # Sort by updated_at ascending (oldest first) and drop until within cap.
            items = sorted(self._buckets.items(), key=lambda kv: kv[1].updated_at)
            overflow = len(items) - self._max_entries
            for i in range(max(0, overflow)):
                self._buckets.pop(items[i][0], None)

        self._last_gc = now

    @staticmethod
    def _refill(bucket: _TokenBucket, limit: RateLimit, now: float) -> None:
        elapsed = max(0.0, now - bucket.updated_at)
        bucket.updated_at = now
        bucket.tokens = min(
            float(limit.burst), bucket.tokens + elapsed * limit.rate_per_sec
        )

    def consume(self, *, principal_key: str, action: str, tokens: float = 1.0) -> None:
        """
        Consume tokens from the bucket for a given principal+action.

        Raises RateLimitExceeded if insufficient tokens.
        """
        if not principal_key:
            # If you pass empty principal keys, you risk collapsing all users into one bucket.
            principal_key = "anonymous"

        limit = self.get_limit(action)
        if limit is None:
            # No limit configured for this action.
            return

        now = self._now()
        with self._lock:
            self._maybe_gc(now)

            key = (principal_key, action)
            bucket = self._buckets.get(key)
            if bucket is None:
                # Start with a full bucket to allow initial burst.
                bucket = _TokenBucket(tokens=float(limit.burst), updated_at=now)
                self._buckets[key] = bucket

            self._refill(bucket, limit, now)

            if bucket.tokens >= tokens:
                bucket.tokens -= tokens
                return

            # Compute retry-after: how long until enough tokens are available.
            deficit = max(0.0, tokens - bucket.tokens)
            retry_after = deficit / max(0.000001, limit.rate_per_sec)
            raise RateLimitExceeded(action=action, retry_after_seconds=retry_after)


def hash_token_for_rl(token: str) -> str:
    """
    Hash a raw API token into a stable principal key for in-memory limiting.

    This avoids storing raw tokens in memory/logs and prevents high-cardinality keys.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def enforce_json_size_guardrail(*, raw_body: bytes, max_bytes: int) -> None:
    """
    Enforce an upper bound on raw request size.

    This should be called on the raw bytes of the request body.
    FastAPI/Starlette also have server/proxy-level limits; treat this as a second line of defense.

    Raises PayloadTooLarge if limit exceeded.
    """
    actual = len(raw_body or b"")
    if actual > int(max_bytes):
        raise PayloadTooLarge(max_bytes=int(max_bytes), actual_bytes=actual)


# -------------------------
# Recommended defaults
# -------------------------

DEFAULT_LIMITS: Dict[str, RateLimit] = {
    # Producers
    # - enqueue: allow modest sustained rate with burst
    "enqueue": RateLimit(rate_per_sec=5.0, burst=20),
    # Dashboard/listing endpoints can be less frequent
    "list_jobs": RateLimit(rate_per_sec=2.0, burst=10),
    "queue_stats": RateLimit(rate_per_sec=2.0, burst=10),
    # Workers
    "lease": RateLimit(rate_per_sec=10.0, burst=30),
    "ack": RateLimit(rate_per_sec=20.0, burst=50),
    "nack": RateLimit(rate_per_sec=20.0, burst=50),
    "heartbeat": RateLimit(rate_per_sec=20.0, burst=50),
}

# Default payload size limits (bytes). Adjust for your environment.
DEFAULT_MAX_ENQUEUE_PAYLOAD_BYTES = 256 * 1024  # 256 KiB
DEFAULT_MAX_RESULT_PAYLOAD_BYTES = 256 * 1024  # 256 KiB
DEFAULT_MAX_ERROR_TEXT_BYTES = 8 * 1024  # 8 KiB
