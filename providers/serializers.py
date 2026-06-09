"""Serializers for providers."""
from django.contrib.auth import get_user_model
from rest_framework import serializers

from providers.models import Provider

User = get_user_model()


class ProviderSerializer(serializers.ModelSerializer):
    """Serialize provider profiles."""

    user_email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = Provider
        fields = (
            "id",
            "user",
            "user_email",
            "first_name",
            "last_name",
            "specialization",
            "medical_license_number",
            "experience_years",
            "bio",
            "consultation_fee",
            "is_verified",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_user(self, value):
        if value.role != User.Roles.DOCTOR:
            raise serializers.ValidationError(
                "Provider profiles can only be linked to doctor users."
            )
        return value

    def validate_specialization(self, value):
        specialization = value.strip()
        if not specialization:
            raise serializers.ValidationError("Specialization is required.")
        return specialization
