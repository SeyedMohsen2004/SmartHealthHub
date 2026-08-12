"""Request-local correlation IDs for logging and response metadata."""

import logging
import re
import uuid
from contextvars import ContextVar

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9._:-]{1,64}\Z", re.ASCII)

_request_id = ContextVar("request_id", default="-")


def resolve_request_id(candidate):
    """Preserve a safe caller ID or generate an independent UUID4 value."""

    if isinstance(candidate, str) and REQUEST_ID_PATTERN.fullmatch(candidate):
        return candidate
    return str(uuid.uuid4())


def get_request_id():
    """Return the active request ID, or the non-request fallback."""

    return _request_id.get()


def set_request_id(request_id):
    """Set the active request ID and return the ContextVar reset token."""

    return _request_id.set(request_id)


def reset_request_id(token):
    """Restore the request context that preceded ``token``."""

    _request_id.reset(token)


class RequestIdFilter(logging.Filter):
    """Attach a safe request ID to every formatted log record."""

    def filter(self, record):
        record.request_id = get_request_id()
        return True
