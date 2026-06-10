"""Admin configuration for providers."""

from django.contrib import admin

from providers.models import Provider


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    """Admin registration for healthcare providers."""

    list_display = (
        "id",
        "user",
        "specialization",
        "medical_license_number",
        "experience_years",
        "consultation_fee",
        "is_verified",
        "created_at",
    )
    list_filter = ("specialization", "is_verified", "created_at")
    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "specialization",
        "medical_license_number",
    )
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
