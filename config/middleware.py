"""Small project-level middleware components."""

import logging
import time

from .request_context import (
    REQUEST_ID_HEADER,
    reset_request_id,
    resolve_request_id,
    set_request_id,
)

request_logger = logging.getLogger("smarthealthhub.request")


class RequestContextMiddleware:
    """Correlate a request, its response, and safe completion metadata."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
        token = set_request_id(request_id)
        started_at = time.monotonic()
        response = None

        try:
            response = self.get_response(request)
            response[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            duration_ms = (time.monotonic() - started_at) * 1000
            request_logger.info(
                "request_completed method=%s path=%s status=%s duration_ms=%.2f",
                request.method,
                request.path,
                response.status_code if response is not None else 500,
                duration_ms,
            )
            reset_request_id(token)
