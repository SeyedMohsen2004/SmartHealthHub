"""Production settings with fail-fast environment validation."""

from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403
from .base import DATABASES as BASE_DATABASES

DEBUG = False


def required_string(name):
    """Return a non-empty production setting or fail during startup."""

    value = config(name)
    if not value.strip():
        raise ImproperlyConfigured(f"{name} must be set to a non-empty value.")
    return value


# Never inherit development credential or host fallbacks in production.
SECRET_KEY = required_string("DJANGO_SECRET_KEY")
if len(SECRET_KEY) < 32:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be at least 32 characters.")

ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", cast=Csv())
if not ALLOWED_HOSTS or any(not host.strip() for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must contain valid hosts.")

DATABASES = {
    "default": {
        **BASE_DATABASES["default"],
        "NAME": required_string("POSTGRES_DB"),
        "USER": required_string("POSTGRES_USER"),
        "PASSWORD": required_string("POSTGRES_PASSWORD"),
        "HOST": required_string("POSTGRES_HOST"),
        "PORT": config("POSTGRES_PORT", default="5432"),
    }
}

if config("DJANGO_TRUST_X_FORWARDED_PROTO", default=False, cast=bool):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = config("DJANGO_SECURE_SSL_REDIRECT", default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = config("DJANGO_SECURE_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
