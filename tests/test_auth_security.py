from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.throttling import (
    AnonRateThrottle,
    BaseThrottle,
    ScopedRateThrottle,
    UserRateThrottle,
)
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.serializers import INVALID_REFRESH_MESSAGE

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_throttle_state():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def set_throttle_rates(monkeypatch):
    def configure(**overrides):
        rates = {
            "anon": "1000/min",
            "user": "1000/min",
            "auth_register": "1000/min",
            "auth_login": "1000/min",
            "auth_refresh": "1000/min",
            "auth_logout": "1000/min",
        }
        rates.update(overrides)
        for throttle_class in (
            AnonRateThrottle,
            UserRateThrottle,
            ScopedRateThrottle,
        ):
            monkeypatch.setattr(throttle_class, "THROTTLE_RATES", rates)
        cache.clear()

    return configure


def create_user(email="auth@example.com", *, is_active=True):
    return User.objects.create_user(
        username=email,
        email=email,
        password="StrongPass123!",
        is_active=is_active,
    )


def login(client, email="auth@example.com"):
    return client.post(
        reverse("api_v1:accounts:login"),
        {"email": email, "password": "StrongPass123!"},
        format="json",
    )


def refresh(client, token):
    return client.post(
        reverse("api_v1:accounts:refresh"),
        {"refresh": token},
        format="json",
    )


def logout(client, token):
    return client.post(
        reverse("api_v1:accounts:logout"),
        {"refresh": token},
        format="json",
    )


@pytest.mark.django_db
def test_login_refresh_tokens_rotate_and_previous_tokens_are_blacklisted(api_client):
    user = create_user()
    login_response = login(api_client)
    first_refresh = login_response.json()["refresh"]
    first_jti = RefreshToken(first_refresh)["jti"]

    first_rotation = refresh(api_client, first_refresh)
    second_refresh = first_rotation.json()["refresh"]
    second_jti = RefreshToken(second_refresh)["jti"]

    assert login_response.status_code == 200
    assert first_rotation.status_code == 200
    assert first_rotation.json()["access"]
    assert second_refresh != first_refresh
    assert OutstandingToken.objects.filter(user=user, jti=first_jti).exists()
    assert BlacklistedToken.objects.filter(token__jti=first_jti).exists()
    assert refresh(api_client, first_refresh).status_code == 401

    second_rotation = refresh(api_client, second_refresh)
    third_refresh = second_rotation.json()["refresh"]

    assert second_rotation.status_code == 200
    assert third_refresh != second_refresh
    assert OutstandingToken.objects.filter(user=user, jti=second_jti).exists()
    assert BlacklistedToken.objects.filter(token__jti=second_jti).exists()
    assert refresh(api_client, second_refresh).status_code == 401


@pytest.mark.django_db
def test_registration_refresh_token_rotates_and_is_recorded(api_client):
    registration = api_client.post(
        reverse("api_v1:accounts:register"),
        {
            "email": "registered@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        },
        format="json",
    )
    first_refresh = registration.json()["tokens"]["refresh"]
    first_jti = RefreshToken(first_refresh)["jti"]

    rotation = refresh(api_client, first_refresh)

    assert registration.status_code == 201
    assert registration.json()["tokens"]["access"]
    assert rotation.status_code == 200
    assert rotation.json()["refresh"] != first_refresh
    assert OutstandingToken.objects.filter(jti=first_jti).exists()
    assert BlacklistedToken.objects.filter(token__jti=first_jti).exists()
    assert refresh(api_client, first_refresh).status_code == 401


@pytest.mark.django_db
def test_logout_revokes_supplied_refresh_without_access_authentication(api_client):
    create_user()
    token = login(api_client).json()["refresh"]
    jti = RefreshToken(token)["jti"]
    api_client.credentials(HTTP_AUTHORIZATION="Bearer malformed-access-token")

    response = logout(api_client, token)

    api_client.credentials()
    assert response.status_code == 204
    assert response.content == b""
    assert BlacklistedToken.objects.filter(token__jti=jti).exists()
    assert refresh(api_client, token).status_code == 401


@pytest.mark.django_db
def test_logout_revokes_only_one_independent_session(api_client):
    create_user()
    first_refresh = login(api_client).json()["refresh"]
    second_refresh = login(api_client).json()["refresh"]

    assert logout(api_client, first_refresh).status_code == 204
    assert refresh(api_client, first_refresh).status_code == 401
    assert refresh(api_client, second_refresh).status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("token", ["malformed", ""])
def test_logout_rejects_malformed_refresh_with_stable_400(api_client, token):
    response = logout(api_client, token)

    assert response.status_code == 400
    assert response.json() == {"refresh": [INVALID_REFRESH_MESSAGE]}


@pytest.mark.django_db
def test_logout_rejects_expired_refresh_with_stable_400(api_client):
    user = create_user()
    token = RefreshToken.for_user(user)
    token.set_exp(from_time=timezone.now(), lifetime=timedelta(seconds=-1))

    response = logout(api_client, str(token))

    assert response.status_code == 400
    assert response.json() == {"refresh": [INVALID_REFRESH_MESSAGE]}


@pytest.mark.django_db
def test_logout_rejects_already_revoked_refresh_with_stable_400(api_client):
    create_user()
    token = login(api_client).json()["refresh"]

    assert logout(api_client, token).status_code == 204
    second_logout = logout(api_client, token)

    assert second_logout.status_code == 400
    assert second_logout.json() == {"refresh": [INVALID_REFRESH_MESSAGE]}


@pytest.mark.django_db
def test_existing_access_token_survives_refresh_rotation_and_logout(api_client):
    create_user()
    rotated_pair = login(api_client).json()
    rotated_access = rotated_pair["access"]
    rotated_refresh = rotated_pair["refresh"]

    assert refresh(api_client, rotated_refresh).status_code == 200

    authenticated_client = APIClient()
    authenticated_client.credentials(HTTP_AUTHORIZATION=f"Bearer {rotated_access}")
    profile_after_rotation = authenticated_client.get(
        reverse("api_v1:accounts:profile")
    )

    logged_out_pair = login(api_client).json()
    assert logout(api_client, logged_out_pair["refresh"]).status_code == 204
    authenticated_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {logged_out_pair['access']}"
    )
    profile_after_logout = authenticated_client.get(reverse("api_v1:accounts:profile"))

    assert profile_after_rotation.status_code == 200
    assert profile_after_logout.status_code == 200
    assert profile_after_logout.json()["email"] == "auth@example.com"


@pytest.mark.django_db
def test_inactive_user_cannot_rotate_existing_refresh(api_client):
    user = create_user()
    token = login(api_client).json()["refresh"]
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = refresh(api_client, token)

    assert response.status_code == 401


@pytest.mark.django_db
def test_failed_logins_consume_login_scope_budget(api_client, set_throttle_rates):
    create_user()
    set_throttle_rates(auth_login="2/min")

    first = api_client.post(
        reverse("api_v1:accounts:login"),
        {"email": "auth@example.com", "password": "wrong"},
        format="json",
    )
    second = api_client.post(
        reverse("api_v1:accounts:login"),
        {"email": "auth@example.com", "password": "wrong"},
        format="json",
    )
    throttled = login(api_client)

    assert first.status_code == 400
    assert second.status_code == 400
    assert throttled.status_code == 429
    assert int(throttled["Retry-After"]) > 0


@pytest.mark.django_db
def test_registration_and_login_scopes_are_isolated(api_client, set_throttle_rates):
    set_throttle_rates(auth_register="1/min", auth_login="1/min")
    registration_payload = {
        "email": "scope@example.com",
        "password": "StrongPass123!",
        "password_confirm": "StrongPass123!",
    }

    first_registration = api_client.post(
        reverse("api_v1:accounts:register"),
        registration_payload,
        format="json",
    )
    second_registration = api_client.post(
        reverse("api_v1:accounts:register"),
        {**registration_payload, "email": "other@example.com"},
        format="json",
    )
    login_response = login(api_client, email="scope@example.com")

    assert first_registration.status_code == 201
    assert second_registration.status_code == 429
    assert login_response.status_code == 200


@pytest.mark.django_db
def test_refresh_scope_throttles_after_successful_rotations(
    api_client,
    set_throttle_rates,
):
    create_user()
    set_throttle_rates(auth_refresh="2/min")
    first_refresh = login(api_client).json()["refresh"]

    first_rotation = refresh(api_client, first_refresh)
    second_rotation = refresh(api_client, first_rotation.json()["refresh"])
    throttled = refresh(api_client, second_rotation.json()["refresh"])

    assert first_rotation.status_code == 200
    assert second_rotation.status_code == 200
    assert throttled.status_code == 429


@pytest.mark.django_db
def test_logout_scope_throttles_without_revoking_later_token(
    api_client,
    set_throttle_rates,
):
    create_user()
    set_throttle_rates(auth_logout="1/min")
    first_refresh = login(api_client).json()["refresh"]
    second_refresh = login(api_client).json()["refresh"]

    allowed = logout(api_client, first_refresh)
    throttled = logout(api_client, second_refresh)

    assert allowed.status_code == 204
    assert throttled.status_code == 429
    assert refresh(api_client, second_refresh).status_code == 200


@pytest.mark.django_db
def test_authenticated_profile_uses_global_user_throttle(
    api_client,
    set_throttle_rates,
):
    user = create_user()
    set_throttle_rates(user="1/min")
    api_client.force_authenticate(user=user)

    first = api_client.get(reverse("api_v1:accounts:profile"))
    throttled = api_client.get(reverse("api_v1:accounts:profile"))

    assert first.status_code == 200
    assert throttled.status_code == 429


@pytest.mark.django_db
def test_health_endpoint_is_exempt_from_anonymous_throttling(
    api_client,
    set_throttle_rates,
):
    set_throttle_rates(anon="1/min")

    responses = [api_client.get(reverse("api_v1:health-check")) for _ in range(3)]

    assert [response.status_code for response in responses] == [200, 200, 200]


def test_default_throttle_policy_and_num_proxies_are_explicit():
    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    request = APIRequestFactory().get(
        "/",
        REMOTE_ADDR="192.0.2.10",
        HTTP_X_FORWARDED_FOR="198.51.100.20, 203.0.113.30",
    )

    assert rates == {
        "anon": "100/hour",
        "user": "1000/hour",
        "auth_register": "5/hour",
        "auth_login": "10/min",
        "auth_refresh": "30/min",
        "auth_logout": "30/min",
    }
    assert settings.REST_FRAMEWORK["NUM_PROXIES"] == 0
    assert BaseThrottle().get_ident(request) == "192.0.2.10"
