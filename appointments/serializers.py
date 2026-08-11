"""Serializers for appointments."""

from django.utils import timezone
from rest_framework import serializers

from appointments.models import Appointment
from appointments.services import (
    AppointmentMutationError,
    create_appointment,
    update_appointment,
    validate_appointment_changes,
    validate_new_appointment,
)


class AppointmentSerializer(serializers.ModelSerializer):
    """Serialize appointment records for reads and admin updates."""

    patient_email = serializers.EmailField(source="patient.email", read_only=True)
    provider_specialization = serializers.CharField(
        source="provider.specialization",
        read_only=True,
    )
    provider_email = serializers.EmailField(
        source="provider.user.email",
        read_only=True,
    )

    class Meta:
        model = Appointment
        fields = (
            "id",
            "patient",
            "patient_email",
            "provider",
            "provider_email",
            "provider_specialization",
            "appointment_date",
            "appointment_time",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "patient", "created_at", "updated_at")
        validators = []

    def validate_appointment_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError("Appointment date cannot be in the past.")
        return value

    def validate(self, attrs):
        provider = attrs.get("provider", getattr(self.instance, "provider", None))
        appointment_date = attrs.get(
            "appointment_date",
            getattr(self.instance, "appointment_date", None),
        )
        appointment_time = attrs.get(
            "appointment_time",
            getattr(self.instance, "appointment_time", None),
        )

        try:
            if self.instance is None:
                if provider and appointment_date and appointment_time:
                    validate_new_appointment(
                        provider=provider,
                        appointment_date=appointment_date,
                        appointment_time=appointment_time,
                    )
            else:
                validate_appointment_changes(self.instance, attrs)
        except AppointmentMutationError as exc:
            raise serializers.ValidationError(exc.detail) from exc

        return attrs

    def update(self, instance, validated_data):
        try:
            return update_appointment(
                appointment_id=instance.pk,
                validated_data=validated_data,
            )
        except AppointmentMutationError as exc:
            raise serializers.ValidationError(exc.detail) from exc


class AppointmentCreateSerializer(AppointmentSerializer):
    """Validate and create patient-owned appointments."""

    class Meta(AppointmentSerializer.Meta):
        read_only_fields = (
            "id",
            "patient",
            "status",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data):
        request = self.context["request"]
        try:
            return create_appointment(
                patient=request.user,
                validated_data=validated_data,
            )
        except AppointmentMutationError as exc:
            raise serializers.ValidationError(exc.detail) from exc
