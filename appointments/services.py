"""Transactional appointment-domain mutations and invariants."""

from datetime import datetime

from django.db import IntegrityError, transaction
from django.utils import timezone

from appointments.models import Appointment

ACTIVE_SLOT_CONSTRAINT = "unique_active_provider_appointment_slot"
SLOT_CONFLICT_MESSAGE = (
    "This provider already has an active appointment at this date and time."
)
TERMINAL_RESCHEDULE_MESSAGE = (
    "Cancelled and completed appointments cannot be rescheduled."
)
FUTURE_APPOINTMENT_MESSAGE = "Appointment time must be in the future."
FUTURE_COMPLETION_MESSAGE = "A future appointment cannot be marked as completed."

SCHEDULING_FIELDS = ("provider", "appointment_date", "appointment_time")
RESCHEDULABLE_STATUSES = {
    Appointment.Status.PENDING,
    Appointment.Status.CONFIRMED,
}
ALLOWED_STATUS_TRANSITIONS = {
    Appointment.Status.PENDING: {
        Appointment.Status.CONFIRMED,
        Appointment.Status.CANCELLED,
    },
    Appointment.Status.CONFIRMED: {
        Appointment.Status.COMPLETED,
        Appointment.Status.CANCELLED,
    },
    Appointment.Status.CANCELLED: set(),
    Appointment.Status.COMPLETED: set(),
}


class AppointmentMutationError(Exception):
    """A stable, user-facing appointment validation failure."""

    def __init__(self, detail):
        self.detail = detail
        super().__init__(str(detail))


def scheduled_datetime(appointment_date, appointment_time):
    """Return the scheduled local date/time as an aware datetime."""

    return timezone.make_aware(
        datetime.combine(appointment_date, appointment_time),
        timezone.get_current_timezone(),
    )


def active_slot_is_taken(
    *,
    provider,
    appointment_date,
    appointment_time,
    exclude_appointment_id=None,
):
    """Check for a friendly early conflict; the database remains authoritative."""

    queryset = Appointment.objects.exclude(status=Appointment.Status.CANCELLED).filter(
        provider=provider,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
    )
    if exclude_appointment_id is not None:
        queryset = queryset.exclude(pk=exclude_appointment_id)
    return queryset.exists()


def _validate_future_schedule(appointment_date, appointment_time, *, now=None):
    if scheduled_datetime(appointment_date, appointment_time) <= (
        now or timezone.now()
    ):
        raise AppointmentMutationError({"appointment_time": FUTURE_APPOINTMENT_MESSAGE})


def _validate_status_transition(
    appointment,
    new_status,
    *,
    appointment_date=None,
    appointment_time=None,
    now=None,
):
    current_status = appointment.status
    if new_status == current_status:
        return

    if new_status not in ALLOWED_STATUS_TRANSITIONS[current_status]:
        raise AppointmentMutationError(
            {
                "status": (
                    f"Transition from {current_status} to {new_status} is not allowed."
                )
            }
        )

    if new_status == Appointment.Status.COMPLETED and scheduled_datetime(
        (
            appointment_date
            if appointment_date is not None
            else appointment.appointment_date
        ),
        (
            appointment_time
            if appointment_time is not None
            else appointment.appointment_time
        ),
    ) > (now or timezone.now()):
        raise AppointmentMutationError({"status": FUTURE_COMPLETION_MESSAGE})


def validate_new_appointment(*, provider, appointment_date, appointment_time, now=None):
    """Validate a new active appointment before attempting its insert."""

    _validate_future_schedule(appointment_date, appointment_time, now=now)
    if active_slot_is_taken(
        provider=provider,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
    ):
        raise AppointmentMutationError({"non_field_errors": [SLOT_CONFLICT_MESSAGE]})


def validate_appointment_changes(appointment, changes, *, now=None):
    """Validate changes against the current appointment state."""

    resulting_values = {
        field: changes.get(field, getattr(appointment, field))
        for field in SCHEDULING_FIELDS
    }
    scheduling_changed = any(
        field in changes and changes[field] != getattr(appointment, field)
        for field in SCHEDULING_FIELDS
    )

    new_status = changes.get("status", appointment.status)
    _validate_status_transition(
        appointment,
        new_status,
        appointment_date=resulting_values["appointment_date"],
        appointment_time=resulting_values["appointment_time"],
        now=now,
    )

    if scheduling_changed:
        if appointment.status not in RESCHEDULABLE_STATUSES:
            raise AppointmentMutationError(
                {"non_field_errors": [TERMINAL_RESCHEDULE_MESSAGE]}
            )
        _validate_future_schedule(
            resulting_values["appointment_date"],
            resulting_values["appointment_time"],
            now=now,
        )

    if scheduling_changed and new_status != Appointment.Status.CANCELLED:
        if active_slot_is_taken(
            **resulting_values,
            exclude_appointment_id=appointment.pk,
        ):
            raise AppointmentMutationError(
                {"non_field_errors": [SLOT_CONFLICT_MESSAGE]}
            )


def _is_active_slot_conflict(exc):
    cause = getattr(exc, "__cause__", None)
    diagnostic = getattr(cause, "diag", None)
    return getattr(diagnostic, "constraint_name", None) == ACTIVE_SLOT_CONSTRAINT


def create_appointment(*, patient, validated_data):
    """Create a patient-owned appointment within a short transaction."""

    try:
        with transaction.atomic():
            validate_new_appointment(**validated_data)
            return Appointment.objects.create(
                patient=patient,
                status=Appointment.Status.PENDING,
                **validated_data,
            )
    except IntegrityError as exc:
        if not _is_active_slot_conflict(exc):
            raise
        raise AppointmentMutationError(
            {"non_field_errors": [SLOT_CONFLICT_MESSAGE]}
        ) from exc


def update_appointment(*, appointment_id, validated_data):
    """Lock, revalidate, and update an appointment without lost writes."""

    try:
        with transaction.atomic():
            appointment = Appointment.objects.select_for_update().get(pk=appointment_id)
            validate_appointment_changes(appointment, validated_data)

            changes = {
                field: value
                for field, value in validated_data.items()
                if value != getattr(appointment, field)
            }
            if not changes:
                return appointment

            for field, value in changes.items():
                setattr(appointment, field, value)
            appointment.save()
            return appointment
    except IntegrityError as exc:
        if not _is_active_slot_conflict(exc):
            raise
        raise AppointmentMutationError(
            {"non_field_errors": [SLOT_CONFLICT_MESSAGE]}
        ) from exc
