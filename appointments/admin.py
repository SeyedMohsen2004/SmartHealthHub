"""Admin configuration for appointments."""
from django.contrib import admin

from appointments.models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """Admin registration for appointments."""

    list_display = (
        "id",
        "patient",
        "provider",
        "appointment_date",
        "appointment_time",
        "status",
        "created_at",
    )
    list_filter = ("status", "appointment_date", "provider")
    search_fields = (
        "patient__email",
        "provider__user__email",
        "provider__specialization",
    )
    readonly_fields = ("created_at", "updated_at")
    ordering = ("appointment_date", "appointment_time")
