from __future__ import annotations

import logging
import time
import uuid
from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .metrics import HTTP_REQUEST_DURATION_SECONDS, HTTP_REQUESTS_TOTAL


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that ensures every request has a request id.

    - Reads an incoming request id from `X-Request-ID` (if provided).
    - Otherwise generates a new UUID4.
    - Attaches it to:
        - request.state.request_id
        - response header `X-Request-ID`
    """

    def __init__(
        self,
        app,
        header_name: str = "X-Request-ID",
        request_state_key: str = "request_id",
    ):
        super().__init__(app)
        self.header_name = header_name
        self.request_state_key = request_state_key

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        incoming = request.headers.get(self.header_name)
        request_id = (incoming or "").strip() or str(uuid.uuid4())

        setattr(request.state, self.request_state_key, request_id)

        response = await call_next(request)
        response.headers[self.header_name] = request_id
        return response


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Lightweight structured logging middleware.

    Produces a single log line per request with a consistent set of fields.
    Intended to be JSON-like but does not require a JSON logger.

    Fields included:
    - request_id
    - method
    - path
    - status_code
    - duration_ms
    - client_ip
    - user_agent
    """

    def __init__(
        self,
        app,
        logger: Optional[logging.Logger] = None,
        request_id_state_key: str = "request_id",
    ):
        super().__init__(app)
        self.logger = logger or logging.getLogger("openqueue.http")
        self.request_id_state_key = request_id_state_key

    @staticmethod
    def _client_ip(request: Request) -> Optional[str]:
        # If you deploy behind a proxy, configure uvicorn/proxy headers accordingly.
        if request.client is None:
            return None
        return request.client.host

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0
            request_id = getattr(request.state, self.request_id_state_key, None)

            # Keep it JSON-ish so it works well in log aggregators.
            self.logger.info(
                "http_request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 3),
                    "client_ip": self._client_ip(request),
                    "user_agent": request.headers.get("user-agent"),
                },
            )


class PrometheusHttpMetricsMiddleware(BaseHTTPMiddleware):
    """
    Prometheus HTTP metrics middleware.

    Records:
    - openqueue_http_requests_total{method,path,status_code}
    - openqueue_http_request_duration_seconds{method,path}

    Notes:
    - `path` is taken as the raw request path. If you want route templates
      (e.g. /jobs/{job_id}) to reduce label cardinality, you can enhance this
      later by reading the matched route from the scope.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        method = request.method
        path = request.url.path

        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_seconds = time.perf_counter() - start

            HTTP_REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(
                duration_seconds
            )
            HTTP_REQUESTS_TOTAL.labels(
                method=method, path=path, status_code=str(status_code)
            ).inc()
