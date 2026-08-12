import io
import logging
import re

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle

from config.request_context import (
    REQUEST_ID_PATTERN,
    RequestIdFilter,
    get_request_id,
)


@pytest.fixture
def request_log():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(logging.Formatter("request_id=%(request_id)s %(message)s"))
    logger = logging.getLogger("smarthealthhub.request")
    logger.addHandler(handler)
    try:
        yield stream
    finally:
        logger.removeHandler(handler)
        handler.close()


@pytest.mark.django_db
def test_missing_request_id_is_generated_and_returned(api_client):
    response = api_client.get(reverse("api_v1:health-check"))

    request_id = response["X-Request-ID"]
    assert REQUEST_ID_PATTERN.fullmatch(request_id)
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
        request_id,
    )
    assert response.json() == {"status": "ok", "database": "ok"}


@pytest.mark.django_db
def test_safe_caller_request_id_is_preserved(api_client):
    response = api_client.get(
        reverse("api_v1:health-check"),
        HTTP_X_REQUEST_ID="client.trace_42:part-1",
    )

    assert response["X-Request-ID"] == "client.trace_42:part-1"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "unsafe_request_id",
    [
        "contains spaces",
        "line-one\nline-two",
        "control\x00character",
        "non-ascii-é",
        "x" * 65,
    ],
)
def test_unsafe_caller_request_id_is_replaced(
    api_client,
    request_log,
    unsafe_request_id,
):
    response = api_client.get(
        reverse("api_v1:health-check"),
        HTTP_X_REQUEST_ID=unsafe_request_id,
    )

    request_id = response["X-Request-ID"]
    assert request_id != unsafe_request_id
    assert REQUEST_ID_PATTERN.fullmatch(request_id)
    assert unsafe_request_id not in request_log.getvalue()


@pytest.mark.django_db
def test_completion_log_contains_only_safe_request_metadata(api_client, request_log):
    response = api_client.get(
        f'{reverse("api_v1:health-check")}?patient=private-value',
        HTTP_X_REQUEST_ID="safe-correlation-id",
        HTTP_AUTHORIZATION="Bearer secret-jwt-value",
    )

    log_message = request_log.getvalue()
    assert response.status_code == 200
    assert "request_id=safe-correlation-id" in log_message
    assert "request_completed" in log_message
    assert "method=GET" in log_message
    assert f'path={reverse("api_v1:health-check")}' in log_message
    assert "status=200" in log_message
    assert re.search(r"duration_ms=\d+\.\d{2}", log_message)
    assert "private-value" not in log_message
    assert "secret-jwt-value" not in log_message


@pytest.mark.django_db
def test_sequential_requests_do_not_share_context(api_client, request_log):
    first = api_client.get(
        reverse("api_v1:health-check"), HTTP_X_REQUEST_ID="first-request"
    )
    second = api_client.get(
        reverse("api_v1:health-check"), HTTP_X_REQUEST_ID="second-request"
    )

    assert first["X-Request-ID"] == "first-request"
    assert second["X-Request-ID"] == "second-request"
    assert get_request_id() == "-"
    assert "request_id=first-request" in request_log.getvalue()
    assert "request_id=second-request" in request_log.getvalue()


def test_logging_filter_uses_non_request_fallback():
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "ready", (), None)

    assert RequestIdFilter().filter(record) is True
    assert record.request_id == "-"


@pytest.mark.django_db
def test_not_found_response_has_request_id(api_client):
    response = api_client.get("/api/v1/not-a-real-endpoint/")

    assert response.status_code == 404
    assert REQUEST_ID_PATTERN.fullmatch(response["X-Request-ID"])


@pytest.mark.django_db
def test_throttled_response_has_request_id(api_client, monkeypatch):
    rates = {"anon": "1000/min", "auth_login": "1/min"}
    monkeypatch.setattr(AnonRateThrottle, "THROTTLE_RATES", rates)
    monkeypatch.setattr(ScopedRateThrottle, "THROTTLE_RATES", rates)
    cache.clear()
    login_url = reverse("api_v1:accounts:login")

    api_client.post(
        login_url,
        {"email": "missing@example.com", "password": "wrong"},
        format="json",
    )
    response = api_client.post(
        login_url,
        {"email": "missing@example.com", "password": "wrong"},
        format="json",
    )

    assert response.status_code == 429
    assert REQUEST_ID_PATTERN.fullmatch(response["X-Request-ID"])
    cache.clear()
