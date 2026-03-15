"""
Vercel Python serverless entry point.

Vercel's @vercel/python builder requires the ASGI app to be importable
from a file inside api/. This shim adds the repo root to sys.path so
that the 'app' package (app/fastapi_app.py) resolves correctly, then
re-exports the FastAPI app object as `app`.
"""

import os
import sys

# Ensure the repo root is on sys.path so 'app.*' imports resolve.
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from app.fastapi_app import app  # noqa: E402  re-exported for Vercel
