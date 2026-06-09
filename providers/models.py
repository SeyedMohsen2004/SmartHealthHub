"""Providers data models."""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Provider(models.Model):
    """Healthcare provider profile linked to a doctor user account."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="provider_profile",
    )
    specialization = models.CharField(max_length=120)
    medical_license_number = models.CharField(max_length=100, unique=True)
    experience_years = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(80)]
    )
    bio = models.TextField(blank=True)
    consultation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["specialization"]),
            models.Index(fields=["is_verified"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.get_full_name() or self.user.email} - {self.specialization}"
