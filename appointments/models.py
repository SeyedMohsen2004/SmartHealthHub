"""Appointments data models."""

from django.conf import settings
from django.db import models

from providers.models import Provider


class Appointment(models.Model):
    """Appointment booked by a patient with a healthcare provider."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_appointments",
    )
    provider = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("appointment_date", "appointment_time")
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "appointment_date", "appointment_time"],
                name="unique_provider_appointment_slot",
            )
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["appointment_date"]),
            models.Index(fields=["provider", "appointment_date"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.patient.email} with {self.provider.user.email} "
            f"on {self.appointment_date} at {self.appointment_time}"
        )
