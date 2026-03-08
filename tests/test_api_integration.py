from __future__ import annotations

import os
import hashlib
import hmac
import asyncio
import uuid
from typing import Iterator

import asyncpg
import httpx
import pytest


def _unique_queue(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _hmac_sha256_hex(secret: str, value: str) -> str:
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=value.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


@pytest.fixture(scope="session")
def api_base_url() -> str:
    return os.getenv("OPENQUEUE_API_URL", "http://localhost:8000").rstrip("/")


@pytest.fixture(scope="session")
def api_token() -> str:
    return os.getenv(
        "OPENQUEUE_API_TOKEN",
        "oq_test_integration_token",
    )


@pytest.fixture(scope="session")
def database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://openqueue:openqueue_password@localhost:5432/openqueue",
    )


@pytest.fixture(scope="session")
def client(api_base_url: str) -> Iterator[httpx.Client]:
    client = httpx.Client(base_url=api_base_url, timeout=10.0)
    try:
        health = client.get("/health")
        if health.status_code != 200:
            pytest.skip(f"API not healthy: status={health.status_code}")
    except httpx.HTTPError as exc:
        pytest.skip(f"API not reachable at {api_base_url}: {exc}")
    yield client
    client.close()


@pytest.fixture
def auth_headers(api_token: str, database_url: str) -> dict[str, str]:
    async def _ensure_user() -> None:
        conn = await asyncpg.connect(database_url)
        try:
            await conn.execute(
                """
                INSERT INTO users (email, api_token_hash, is_active)
                VALUES ($1, $2, TRUE)
                ON CONFLICT (api_token_hash) DO NOTHING
                """,
                "integration-sha@openqueue.local",
                _sha256_hex(api_token),
            )

            # Optional compatibility for environments where API uses HMAC hashing.
            test_secret = os.getenv("OPENQUEUE_TOKEN_HMAC_SECRET", "openqueue-test-secret")
            await conn.execute(
                """
                INSERT INTO users (email, api_token_hash, is_active)
                VALUES ($1, $2, TRUE)
                ON CONFLICT (api_token_hash) DO NOTHING
                """,
                "integration-hmac@openqueue.local",
                _hmac_sha256_hex(test_secret, api_token),
            )
        finally:
            await conn.close()

    asyncio.run(_ensure_user())
    return {"Authorization": f"Bearer {api_token}"}


def test_health_and_ready(client: httpx.Client) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


def test_job_lifecycle_enqueue_lease_heartbeat_ack_detail(
    client: httpx.Client,
    auth_headers: dict[str, str],
) -> None:
    queue_name = _unique_queue("it-lifecycle")

    create = client.post(
        "/jobs",
        headers=auth_headers,
        json={"queue_name": queue_name, "payload": {"task": "lifecycle"}},
    )
    assert create.status_code == 201
    job_id = create.json()["job_id"]

    lease = client.post(
        f"/queues/{queue_name}/lease",
        headers=auth_headers,
        json={"worker_id": "integration-worker", "lease_seconds": 30},
    )
    assert lease.status_code == 200
    leased = lease.json()
    assert leased is not None
    assert leased["job"]["id"] == job_id
    lease_token = leased["lease_token"]

    heartbeat = client.post(
        f"/jobs/{job_id}/heartbeat",
        headers=auth_headers,
        json={"lease_token": lease_token, "lease_seconds": 30},
    )
    assert heartbeat.status_code == 200

    ack = client.post(
        f"/jobs/{job_id}/ack",
        headers=auth_headers,
        json={"lease_token": lease_token, "result": {"ok": True}},
    )
    assert ack.status_code == 200

    detail = client.get(f"/jobs/{job_id}/detail", headers=auth_headers)
    assert detail.status_code == 200
    job = detail.json()
    assert job["status"] == "completed"
    assert job["result"] == {"ok": True}


def test_list_jobs_filters_and_pagination(
    client: httpx.Client,
    auth_headers: dict[str, str],
) -> None:
    queue_name = _unique_queue("it-list")

    for idx in range(3):
        resp = client.post(
            "/jobs",
            headers=auth_headers,
            json={"queue_name": queue_name, "payload": {"idx": idx}},
        )
        assert resp.status_code == 201

    page_1 = client.get(
        "/jobs",
        headers=auth_headers,
        params={"queue_name": queue_name, "status": "pending", "limit": 2, "offset": 0},
    )
    assert page_1.status_code == 200
    body_1 = page_1.json()
    assert body_1["total"] >= 3
    assert body_1["limit"] == 2
    assert body_1["offset"] == 0
    assert len(body_1["items"]) == 2
    assert all(item["status"] == "pending" for item in body_1["items"])

    page_2 = client.get(
        "/jobs",
        headers=auth_headers,
        params={"queue_name": queue_name, "status": "pending", "limit": 2, "offset": 2},
    )
    assert page_2.status_code == 200
    body_2 = page_2.json()
    assert body_2["offset"] == 2
    assert len(body_2["items"]) >= 1


def test_cancel_pending_job(client: httpx.Client, auth_headers: dict[str, str]) -> None:
    queue_name = _unique_queue("it-cancel")
    create = client.post(
        "/jobs",
        headers=auth_headers,
        json={"queue_name": queue_name, "payload": {"task": "cancel-me"}},
    )
    assert create.status_code == 201
    job_id = create.json()["job_id"]

    cancel = client.post(f"/jobs/{job_id}/cancel", headers=auth_headers)
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"

    status_res = client.get(f"/jobs/{job_id}", headers=auth_headers)
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "cancelled"


def test_invalid_job_id_returns_422(
    client: httpx.Client,
    auth_headers: dict[str, str],
) -> None:
    bad_job_id = "not-a-valid-uuid"

    status_res = client.get(f"/jobs/{bad_job_id}", headers=auth_headers)
    assert status_res.status_code == 422

    ack_res = client.post(
        f"/jobs/{bad_job_id}/ack",
        headers=auth_headers,
        json={"lease_token": str(uuid.uuid4()), "result": {"ok": True}},
    )
    assert ack_res.status_code == 422
