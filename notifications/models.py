"""Notifications data models."""

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """User notification."""

    class Kind(models.TextChoices):
        GENERIC = "GENERIC", "Generic"
        APPOINTMENT_REMINDER = "APPOINTMENT_REMINDER", "Appointment reminder"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    title = models.CharField(max_length=255)

    message = models.TextField()

    kind = models.CharField(
        max_length=32,
        choices=Kind.choices,
        default=Kind.GENERIC,
    )

    appointment = models.ForeignKey(
        "appointments.Appointment",
        on_delete=models.SET_NULL,
        related_name="notifications",
        null=True,
        blank=True,
    )

    appointment_scheduled_for = models.DateTimeField(null=True, blank=True)

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["appointment", "appointment_scheduled_for"],
                condition=models.Q(kind="APPOINTMENT_REMINDER"),
                name="unique_appointment_reminder_schedule",
            )
        ]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["is_read"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.title}"
