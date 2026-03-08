from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def _set_test_env() -> None:
    """
    Ensure predictable environment defaults during tests.

    Notes:
    - Tests should set DATABASE_URL explicitly (e.g. via docker-compose or CI).
    - We set a default HMAC secret so token hashing behavior is deterministic if used.
    """
    os.environ.setdefault("OPENQUEUE_TOKEN_HMAC_SECRET", "openqueue-test-secret")
    os.environ.setdefault("OPENQUEUE_ENV", "test")
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql://openqueue:openqueue_password@localhost:5432/openqueue",
    )


# pytest-asyncio guidance (no custom event_loop fixture)
#
# The custom event_loop fixture is deprecated in pytest-asyncio and will error in
# future versions. To control the loop scope, configure pytest-asyncio via
# pyproject.toml or pytest.ini, e.g.:
#
#   [tool.pytest.ini_options]
#   asyncio_mode = "auto"
#   asyncio_default_fixture_loop_scope = "function"
#
# We keep conftest minimal and avoid redefining pytest-asyncio internals.
