"""
Vercel Python API entrypoint.

This module exposes the ASGI app for Vercel serverless deployment.
Vercel automatically handles the ASGI -> WSGI conversion.
"""

from app.fastapi_app import app

handler = app
