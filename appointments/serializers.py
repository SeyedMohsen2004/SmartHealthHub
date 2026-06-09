"""Serializers for appointments."""
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers

from appointments.models import Appointment


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

        if provider and appointment_date and appointment_time:
            queryset = Appointment.objects.filter(
                provider=provider,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
            )
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    "This provider already has an appointment at this date and time."
                )

        return attrs


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

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        try:
            return Appointment.objects.create(
                patient=request.user,
                status=Appointment.Status.PENDING,
                **validated_data,
            )
        except IntegrityError as exc:
            raise serializers.ValidationError(
                "This provider already has an appointment at this date and time."
            ) from exc
