from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connections, transaction
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment
from appointments.services import scheduled_datetime
from notifications import services, tasks
from notifications.models import Notification
from providers.models import Provider

User = get_user_model()


def create_user(email, role):
    return User.objects.create_user(
        username=email,
        email=email,
        password="StrongPass123!",
        role=role,
    )


def create_provider(suffix=""):
    doctor = create_user(f"doctor{suffix}@example.com", User.Roles.DOCTOR)
    return Provider.objects.create(
        user=doctor,
        specialization="Cardiology",
        medical_license_number=f"REMINDER-LICENCE{suffix}",
        experience_years=10,
        consultation_fee="150.00",
        is_verified=True,
    )


def schedule_values(scheduled_for):
    local_schedule = timezone.localtime(scheduled_for)
    return {
        "appointment_date": local_schedule.date(),
        "appointment_time": local_schedule.time().replace(tzinfo=None),
    }


def create_appointment(
    *,
    now,
    offset,
    status=Appointment.Status.PENDING,
    suffix="",
):
    patient = create_user(f"patient{suffix}@example.com", User.Roles.PATIENT)
    provider = create_provider(suffix)
    return Appointment.objects.create(
        patient=patient,
        provider=provider,
        status=status,
        **schedule_values(now + offset),
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status",
    [Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
)
def test_due_active_appointment_creates_one_reminder(status):
    now = timezone.now().replace(microsecond=0)
    appointment = create_appointment(now=now, offset=timedelta(hours=12), status=status)

    created = services.dispatch_due_appointment_reminders(now=now)

    reminder = Notification.objects.get()
    assert created == 1
    assert reminder.user == appointment.patient
    assert reminder.kind == Notification.Kind.APPOINTMENT_REMINDER
    assert reminder.appointment == appointment
    assert reminder.appointment_scheduled_for == scheduled_datetime(
        appointment.appointment_date,
        appointment.appointment_time,
    )
    assert reminder.title == services.REMINDER_TITLE


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("offset", "status"),
    [
        (timedelta(hours=25), Appointment.Status.PENDING),
        (timedelta(hours=12), Appointment.Status.CANCELLED),
        (timedelta(hours=12), Appointment.Status.COMPLETED),
        (timedelta(hours=-1), Appointment.Status.PENDING),
    ],
)
def test_ineligible_appointment_creates_no_reminder(offset, status):
    now = timezone.now().replace(microsecond=0)
    create_appointment(now=now, offset=offset, status=status)

    assert services.dispatch_due_appointment_reminders(now=now) == 0
    assert not Notification.objects.exists()


@pytest.mark.django_db
def test_inside_window_booking_and_recovery_scan_create_reminder():
    now = timezone.now().replace(microsecond=0)
    appointment = create_appointment(now=now, offset=timedelta(hours=2))
    simulated_recovery = now + timedelta(hours=1)

    assert services.dispatch_due_appointment_reminders(now=simulated_recovery) == 1
    assert Notification.objects.get().appointment == appointment


@pytest.mark.django_db
def test_repeated_dispatch_and_task_redelivery_are_idempotent(monkeypatch):
    now = timezone.now().replace(microsecond=0)
    create_appointment(now=now, offset=timedelta(hours=12))
    monkeypatch.setattr(services.timezone, "now", lambda: now)

    assert services.dispatch_due_appointment_reminders(now=now) == 1
    assert services.dispatch_due_appointment_reminders(now=now) == 0
    assert tasks.dispatch_due_appointment_reminders.run() == 0
    assert Notification.objects.count() == 1


@pytest.mark.django_db
def test_bounded_scans_progress_past_existing_current_reminders():
    now = timezone.now().replace(microsecond=0)
    first = create_appointment(
        now=now,
        offset=timedelta(hours=10),
        suffix="-first",
    )
    second = create_appointment(
        now=now,
        offset=timedelta(hours=12),
        suffix="-second",
    )

    assert services.dispatch_due_appointment_reminders(now=now, batch_size=1) == 1
    assert Notification.objects.get().appointment == first
    assert services.dispatch_due_appointment_reminders(now=now, batch_size=1) == 1
    assert set(Notification.objects.values_list("appointment_id", flat=True)) == {
        first.pk,
        second.pk,
    }


@pytest.mark.django_db
def test_reschedule_before_reminder_uses_only_current_schedule():
    now = timezone.now().replace(microsecond=0)
    appointment = create_appointment(now=now, offset=timedelta(hours=12))
    original_schedule = scheduled_datetime(
        appointment.appointment_date,
        appointment.appointment_time,
    )
    new_schedule = now + timedelta(hours=48)
    Appointment.objects.filter(pk=appointment.pk).update(
        **schedule_values(new_schedule)
    )

    assert services.dispatch_due_appointment_reminders(now=now) == 0
    assert not Notification.objects.filter(
        appointment_scheduled_for=original_schedule
    ).exists()

    scan_time = new_schedule - timedelta(hours=12)
    assert services.dispatch_due_appointment_reminders(now=scan_time) == 1
    assert Notification.objects.get().appointment_scheduled_for == scheduled_datetime(
        *schedule_values(new_schedule).values()
    )


@pytest.mark.django_db
def test_reschedule_after_reminder_preserves_history_and_creates_new_snapshot():
    now = timezone.now().replace(microsecond=0)
    appointment = create_appointment(now=now, offset=timedelta(hours=12))
    schedule_a = scheduled_datetime(
        appointment.appointment_date,
        appointment.appointment_time,
    )
    assert services.dispatch_due_appointment_reminders(now=now) == 1

    schedule_b_source = now + timedelta(hours=36)
    Appointment.objects.filter(pk=appointment.pk).update(
        **schedule_values(schedule_b_source)
    )
    assert (
        services.dispatch_due_appointment_reminders(
            now=schedule_b_source - timedelta(hours=12)
        )
        == 1
    )

    snapshots = set(
        Notification.objects.filter(appointment=appointment).values_list(
            "appointment_scheduled_for", flat=True
        )
    )
    assert len(snapshots) == 2
    assert schedule_a in snapshots


@pytest.mark.django_db
def test_generic_notification_defaults_remain_compatible():
    user = create_user("patient@example.com", User.Roles.PATIENT)

    notification = Notification.objects.create(
        user=user,
        title="Generic",
        message="Existing behavior",
    )

    assert notification.kind == Notification.Kind.GENERIC
    assert notification.appointment is None
    assert notification.appointment_scheduled_for is None


@pytest.mark.django_db
def test_generic_notifications_are_not_subject_to_reminder_uniqueness():
    now = timezone.now().replace(microsecond=0)
    appointment = create_appointment(now=now, offset=timedelta(hours=12))
    scheduled_for = scheduled_datetime(
        appointment.appointment_date,
        appointment.appointment_time,
    )
    values = {
        "user": appointment.patient,
        "title": "Generic",
        "message": "Existing behavior",
        "appointment": appointment,
        "appointment_scheduled_for": scheduled_for,
    }

    Notification.objects.create(**values)
    Notification.objects.create(**values)

    assert Notification.objects.count() == 2


@pytest.mark.django_db
def test_deleting_appointment_preserves_reminder_history():
    now = timezone.now().replace(microsecond=0)
    appointment = create_appointment(now=now, offset=timedelta(hours=12))
    services.dispatch_due_appointment_reminders(now=now)
    reminder = Notification.objects.get()
    snapshot = reminder.appointment_scheduled_for

    appointment.delete()

    reminder.refresh_from_db()
    assert reminder.appointment is None
    assert reminder.appointment_scheduled_for == snapshot


@pytest.mark.django_db
def test_locked_candidate_is_revalidated_after_status_change(monkeypatch):
    now = timezone.now().replace(microsecond=0)
    appointment = create_appointment(now=now, offset=timedelta(hours=12))
    monkeypatch.setattr(
        services,
        "_candidate_appointment_ids",
        lambda **kwargs: [appointment.pk],
    )
    Appointment.objects.filter(pk=appointment.pk).update(
        status=Appointment.Status.CANCELLED
    )

    assert services.dispatch_due_appointment_reminders(now=now) == 0
    assert not Notification.objects.exists()


@pytest.mark.django_db
def test_candidate_deleted_before_lock_is_a_safe_no_op(monkeypatch):
    now = timezone.now().replace(microsecond=0)
    appointment = create_appointment(now=now, offset=timedelta(hours=12))
    appointment_id = appointment.pk
    monkeypatch.setattr(
        services,
        "_candidate_appointment_ids",
        lambda **kwargs: [appointment_id],
    )
    appointment.delete()

    assert services.dispatch_due_appointment_reminders(now=now) == 0
    assert not Notification.objects.exists()


@pytest.mark.django_db
def test_provider_name_fallback_avoids_identifier_disclosure():
    now = timezone.now().replace(microsecond=0)
    appointment = create_appointment(now=now, offset=timedelta(hours=12))

    services.dispatch_due_appointment_reminders(now=now)

    reminder = Notification.objects.get()
    assert "your provider" in reminder.message
    assert appointment.provider.user.email not in reminder.message


@pytest.mark.django_db
def test_internal_reminder_metadata_is_not_publicly_mutable(api_client):
    now = timezone.now().replace(microsecond=0)
    appointment = create_appointment(now=now, offset=timedelta(hours=12))
    services.dispatch_due_appointment_reminders(now=now)
    reminder = Notification.objects.get()
    api_client.force_authenticate(user=appointment.patient)

    response = api_client.patch(
        reverse(
            "api_v1:notifications:notification-detail",
            kwargs={"pk": reminder.pk},
        ),
        {
            "kind": Notification.Kind.GENERIC,
            "appointment": None,
            "appointment_scheduled_for": None,
            "is_read": True,
        },
        format="json",
    )

    reminder.refresh_from_db()
    assert response.status_code == 200
    assert reminder.is_read is True
    assert reminder.kind == Notification.Kind.APPOINTMENT_REMINDER
    assert reminder.appointment == appointment
    assert reminder.appointment_scheduled_for is not None
    assert "kind" not in response.json()


@pytest.mark.django_db
def test_schedule_calculation_is_timezone_aware():
    now = timezone.now().replace(microsecond=0)
    appointment = create_appointment(now=now, offset=timedelta(hours=12))

    value = scheduled_datetime(
        appointment.appointment_date,
        appointment.appointment_time,
    )

    assert timezone.is_aware(value)


@pytest.mark.django_db(transaction=True)
def test_database_constraint_rejects_direct_duplicate_reminder():
    now = timezone.now().replace(microsecond=0)
    appointment = create_appointment(now=now, offset=timedelta(hours=12))
    scheduled_for = scheduled_datetime(
        appointment.appointment_date,
        appointment.appointment_time,
    )
    values = {
        "user": appointment.patient,
        "title": services.REMINDER_TITLE,
        "message": "Reminder",
        "kind": Notification.Kind.APPOINTMENT_REMINDER,
        "appointment": appointment,
        "appointment_scheduled_for": scheduled_for,
    }
    Notification.objects.create(**values)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Notification.objects.create(**values)

    assert Notification.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_dispatchers_create_exactly_one_reminder(monkeypatch):
    now = timezone.now().replace(microsecond=0)
    create_appointment(now=now, offset=timedelta(hours=12))
    barrier = Barrier(2)
    original_create = services.create_reminder_for_appointment

    def synchronized_create(*args, **kwargs):
        barrier.wait(timeout=10)
        return original_create(*args, **kwargs)

    monkeypatch.setattr(
        services,
        "create_reminder_for_appointment",
        synchronized_create,
    )

    def dispatch():
        connections.close_all()
        result = services.dispatch_due_appointment_reminders(now=now)
        connections.close_all()
        return result

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: dispatch(), range(2)))

    assert sorted(results) == [0, 1]
    assert Notification.objects.count() == 1
