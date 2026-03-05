"""
OpenQueue Python SDK

A Python client for OpenQueue, a PostgreSQL-backed job queue service.
"""

from .client import OpenQueue
from .exceptions import (
    OpenQueueError,
    JobNotFoundError,
    LeaseTokenError,
    RateLimitError,
    AuthenticationError,
)

__version__ = "0.1.0"

__all__ = [
    "OpenQueue",
    "OpenQueueError",
    "JobNotFoundError",
    "LeaseTokenError",
    "RateLimitError",
    "AuthenticationError",
]
