"""
Vercel Python serverless entry point for OpenQueue FastAPI backend.

Vercel's @vercel/python builder discovers this file via the rewrites rule
in vercel.json. Mangum adapts the ASGI app to AWS Lambda / Vercel's
serverless function interface.
"""

import os
import sys

# Ensure the repo root is on sys.path so 'app.*' imports resolve.
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from mangum import Mangum  # noqa: E402
from app.fastapi_app import app  # noqa: E402

handler = Mangum(app, lifespan="off")
