"""Accounts data models."""
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user model reserved for future authentication requirements."""

    pass
