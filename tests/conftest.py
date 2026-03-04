from __future__ import annotations

import asyncio
import os
from typing import Iterator

import pytest


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """
    Create a session-scoped asyncio event loop for pytest-asyncio.

    Why:
    - Some test suites create many async tests; reusing one loop avoids overhead.
    - Compatible with pytest-asyncio's expectations.
    """
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture(scope="session", autouse=True)
def _set_test_env() -> None:
    """
    Ensure predictable environment defaults during tests.

    Notes:
    - Tests should set DATABASE_URL explicitly (e.g. via Testcontainers) or export it
      before running pytest.
    - We set a default HMAC secret so token hashing behavior is deterministic if used.
    """
    os.environ.setdefault("OPENQUEUE_TOKEN_HMAC_SECRET", "openqueue-test-secret")
    os.environ.setdefault("OPENQUEUE_ENV", "test")


@pytest.fixture
async def anyio_backend() -> str:
    """
    Let httpx/anyio know we're running asyncio.
    """
    return "asyncio"
