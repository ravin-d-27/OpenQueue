from __future__ import annotations

import pytest
from unittest.mock import patch

from app.rate_limit import (
    PayloadTooLarge,
    RateLimit,
    RateLimitExceeded,
    RateLimiter,
    _TokenBucket,
    enforce_json_size_guardrail,
    hash_token_for_rl,
)


def test_refill_caps_bucket_at_burst() -> None:
    limit = RateLimit(rate_per_sec=5.0, burst=20)
    bucket = _TokenBucket(tokens=10.0, updated_at=0.0)

    RateLimiter._refill(bucket, limit, now=3.0)

    assert bucket.tokens == pytest.approx(20.0)
    assert bucket.updated_at == 3.0


def test_consume_decrements_tokens_for_existing_bucket() -> None:
    limiter = RateLimiter(default_limits={"enqueue": RateLimit(rate_per_sec=5.0, burst=20)})
    limiter._buckets[("user-1", "enqueue")] = _TokenBucket(tokens=10.0, updated_at=100.0)

    with patch.object(RateLimiter, "_now", return_value=100.0):
        limiter.consume(principal_key="user-1", action="enqueue", tokens=3.0)

    bucket = limiter._buckets[("user-1", "enqueue")]
    assert bucket.tokens == pytest.approx(7.0)


def test_consume_uses_anonymous_bucket_for_empty_principal() -> None:
    limiter = RateLimiter(default_limits={"enqueue": RateLimit(rate_per_sec=5.0, burst=5)})

    limiter.consume(principal_key="", action="enqueue")

    bucket = limiter._buckets[("anonymous", "enqueue")]
    assert bucket.tokens == pytest.approx(4.0)


def test_consume_raises_with_retry_after_when_bucket_empty() -> None:
    limiter = RateLimiter(default_limits={"enqueue": RateLimit(rate_per_sec=2.0, burst=4)})
    limiter._buckets[("user-1", "enqueue")] = _TokenBucket(tokens=0.5, updated_at=100.0)

    with patch.object(RateLimiter, "_now", return_value=100.0):
        with pytest.raises(RateLimitExceeded) as exc_info:
            limiter.consume(principal_key="user-1", action="enqueue", tokens=2.0)

    err = exc_info.value
    assert err.action == "enqueue"
    assert err.retry_after_seconds == pytest.approx(0.75)


def test_consume_skips_actions_without_configured_limit() -> None:
    limiter = RateLimiter(default_limits={})

    limiter.consume(principal_key="user-1", action="unknown")

    assert limiter._buckets == {}


def test_maybe_gc_removes_idle_buckets_and_enforces_max_entries() -> None:
    limiter = RateLimiter(
        default_limits={"enqueue": RateLimit(rate_per_sec=1.0, burst=1)},
        max_entries=2,
        gc_interval_seconds=1,
        idle_ttl_seconds=10,
    )
    limiter._buckets = {
        ("old", "enqueue"): _TokenBucket(tokens=1.0, updated_at=5.0),
        ("mid", "enqueue"): _TokenBucket(tokens=1.0, updated_at=15.0),
        ("new", "enqueue"): _TokenBucket(tokens=1.0, updated_at=18.0),
    }
    limiter._last_gc = 0.0

    limiter._maybe_gc(now=20.0)

    assert ("old", "enqueue") not in limiter._buckets
    assert len(limiter._buckets) == 2
    assert set(limiter._buckets) == {("mid", "enqueue"), ("new", "enqueue")}


def test_hash_token_for_rl_is_stable_sha256() -> None:
    token = "secret-token"

    assert hash_token_for_rl(token) == (
        "930bbdc51b6aed5c2a5678fd6e28dee7a05e8a4b643cfc0b4427c3efb86c0d94"
    )


def test_enforce_json_size_guardrail_allows_exact_limit() -> None:
    enforce_json_size_guardrail(raw_body=b"1234", max_bytes=4)


def test_enforce_json_size_guardrail_raises_for_oversized_payload() -> None:
    with pytest.raises(PayloadTooLarge) as exc_info:
        enforce_json_size_guardrail(raw_body=b"12345", max_bytes=4)

    err = exc_info.value
    assert err.max_bytes == 4
    assert err.actual_bytes == 5
