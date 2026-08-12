"""Appointment-reminder policy and durable notification dispatch."""

from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import (
    DateTimeField,
    Exists,
    ExpressionWrapper,
    F,
    OuterRef,
    Q,
)
from django.utils import timezone

from appointments.models import Appointment
from appointments.services import scheduled_datetime
from notifications.models import Notification

REMINDER_CONSTRAINT = "unique_appointment_reminder_schedule"
REMINDER_TITLE = "Appointment reminder"
ELIGIBLE_STATUSES = (
    Appointment.Status.PENDING,
    Appointment.Status.CONFIRMED,
)


def _is_duplicate_reminder(exc):
    cause = getattr(exc, "__cause__", None)
    diagnostic = getattr(cause, "diag", None)
    return getattr(diagnostic, "constraint_name", None) == REMINDER_CONSTRAINT


def reminder_window(*, now=None, lead=None):
    """Return aware lower and upper bounds for the current reminder scan."""

    lower_bound = now or timezone.now()
    lead_time = lead or timedelta(hours=settings.APPOINTMENT_REMINDER_LEAD_HOURS)
    return lower_bound, lower_bound + lead_time


def _candidate_appointment_ids(*, lower_bound, upper_bound, batch_size):
    """Select a bounded, indexed set whose schedule falls inside the window."""

    current_timezone = timezone.get_current_timezone()
    local_lower = timezone.localtime(lower_bound, current_timezone)
    local_upper = timezone.localtime(upper_bound, current_timezone)
    lower_time = local_lower.time().replace(tzinfo=None)
    upper_time = local_upper.time().replace(tzinfo=None)
    after_lower = Q(appointment_date__gt=local_lower.date()) | Q(
        appointment_date=local_lower.date(),
        appointment_time__gt=lower_time,
    )
    through_upper = Q(appointment_date__lt=local_upper.date()) | Q(
        appointment_date=local_upper.date(),
        appointment_time__lte=upper_time,
    )
    current_schedule = ExpressionWrapper(
        F("appointment_date") + F("appointment_time"),
        output_field=DateTimeField(),
    )
    matching_reminder = Notification.objects.filter(
        kind=Notification.Kind.APPOINTMENT_REMINDER,
        appointment_id=OuterRef("pk"),
        appointment_scheduled_for=OuterRef("current_schedule"),
    )
    return list(
        Appointment.objects.filter(
            after_lower,
            through_upper,
            status__in=ELIGIBLE_STATUSES,
        )
        .annotate(current_schedule=current_schedule)
        .annotate(has_current_reminder=Exists(matching_reminder))
        .filter(has_current_reminder=False)
        .order_by("appointment_date", "appointment_time", "pk")
        .values_list("pk", flat=True)[:batch_size]
    )


def create_reminder_for_appointment(
    appointment_id,
    *,
    lower_bound,
    upper_bound,
):
    """Revalidate one locked appointment and create its reminder if still due."""

    try:
        with transaction.atomic():
            appointment = (
                Appointment.objects.select_for_update()
                .select_related("patient", "provider__user")
                .get(pk=appointment_id)
            )
            if appointment.status not in ELIGIBLE_STATUSES:
                return False

            scheduled_for = scheduled_datetime(
                appointment.appointment_date,
                appointment.appointment_time,
            )
            if not lower_bound < scheduled_for <= upper_bound:
                return False

            if Notification.objects.filter(
                kind=Notification.Kind.APPOINTMENT_REMINDER,
                appointment=appointment,
                appointment_scheduled_for=scheduled_for,
            ).exists():
                return False

            provider_name = appointment.provider.user.get_full_name().strip()
            if not provider_name:
                provider_name = "your provider"
            Notification.objects.create(
                user=appointment.patient,
                title=REMINDER_TITLE,
                message=(
                    f"Your appointment with {provider_name} is scheduled for "
                    f"{appointment.appointment_date} at "
                    f"{appointment.appointment_time.strftime('%H:%M')}."
                ),
                kind=Notification.Kind.APPOINTMENT_REMINDER,
                appointment=appointment,
                appointment_scheduled_for=scheduled_for,
            )
            return True
    except IntegrityError as exc:
        if _is_duplicate_reminder(exc):
            return False
        raise
    except Appointment.DoesNotExist:
        return False


def dispatch_due_appointment_reminders(*, now=None, lead=None, batch_size=None):
    """Reconcile due appointments into durable, idempotent notifications."""

    lower_bound, upper_bound = reminder_window(now=now, lead=lead)
    effective_batch_size = batch_size or settings.APPOINTMENT_REMINDER_BATCH_SIZE
    candidate_ids = _candidate_appointment_ids(
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        batch_size=effective_batch_size,
    )
    return sum(
        create_reminder_for_appointment(
            appointment_id,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
        )
        for appointment_id in candidate_ids
    )
