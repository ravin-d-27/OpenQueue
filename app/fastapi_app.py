"""
OpenQueue ASGI entrypoint.

This module exposes the `app` object used by Uvicorn/Gunicorn:

    uvicorn app.fastapi_app:app --reload

We keep this file intentionally small and delegate wiring to the app factory.
"""

from __future__ import annotations

from .core.app_factory import create_app

app = create_app(title="OpenQueue", version="0.0.1")
