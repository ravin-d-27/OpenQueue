"""
Vercel entrypoint for OpenQueue FastAPI app.

Vercel auto-detects FastAPI apps at src/index.py and exposes
the `app` instance as a single serverless function.
"""

from app.fastapi_app import app
