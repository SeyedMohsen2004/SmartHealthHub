import importlib
import sys

import pytest
from django.core.exceptions import ImproperlyConfigured


VALID_ENVIRONMENT = {
    "DJANGO_SECRET_KEY": (
        "synthetic-production-secret-key-with-more-than-fifty-characters"
    ),
    "DJANGO_ALLOWED_HOSTS": "api.example.test",
    "POSTGRES_DB": "smarthealthhub",
    "POSTGRES_USER": "smarthealthhub",
    "POSTGRES_PASSWORD": "synthetic-database-password",
    "POSTGRES_HOST": "database.example.test",
    "POSTGRES_PORT": "5432",
    "DJANGO_TRUST_X_FORWARDED_PROTO": "False",
}


def load_production_settings(monkeypatch, **overrides):
    environment = {**VALID_ENVIRONMENT, **overrides}
    for name, value in environment.items():
        monkeypatch.setenv(name, value)

    sys.modules.pop("config.settings.production", None)
    return importlib.import_module("config.settings.production")


def test_production_settings_use_explicit_environment(monkeypatch):
    production = load_production_settings(monkeypatch)

    assert production.SECRET_KEY == VALID_ENVIRONMENT["DJANGO_SECRET_KEY"]
    assert production.ALLOWED_HOSTS == ["api.example.test"]
    assert production.DATABASES["default"]["PASSWORD"] == (
        "synthetic-database-password"
    )
    assert not hasattr(production, "SECURE_PROXY_SSL_HEADER")


def test_forwarded_https_trust_requires_opt_in(monkeypatch):
    production = load_production_settings(
        monkeypatch,
        DJANGO_TRUST_X_FORWARDED_PROTO="True",
    )

    assert production.SECURE_PROXY_SSL_HEADER == (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )


@pytest.mark.parametrize(
    ("name", "value", "message"),
    (
        ("DJANGO_SECRET_KEY", "", "DJANGO_SECRET_KEY must be set"),
        ("DJANGO_SECRET_KEY", "too-short", "at least 32 characters"),
        ("DJANGO_ALLOWED_HOSTS", "", "DJANGO_ALLOWED_HOSTS"),
        ("POSTGRES_PASSWORD", "", "POSTGRES_PASSWORD must be set"),
    ),
)
def test_production_settings_reject_unsafe_environment(
    monkeypatch, name, value, message
):
    with pytest.raises(ImproperlyConfigured, match=message):
        load_production_settings(monkeypatch, **{name: value})
