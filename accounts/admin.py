"""Admin configuration for accounts."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Admin registration for the project user model."""

    list_display = (
        "id",
        "username",
        "email",
        "phone_number",
        "role",
        "is_active",
        "is_staff",
        "created_at",
    )
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email", "phone_number", "first_name", "last_name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "last_login", "date_joined")
    fieldsets = UserAdmin.fieldsets + (
        (
            "SmartHealthHub Profile",
            {"fields": ("phone_number", "role", "created_at", "updated_at")},
        ),
    )
