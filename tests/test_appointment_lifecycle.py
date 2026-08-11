from concurrent.futures import ThreadPoolExecutor
from datetime import time, timedelta
from threading import Barrier

import pytest
from django.contrib.auth import get_user_model
from django.db import connections
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from appointments import services
from appointments.models import Appointment
from providers.models import Provider

User = get_user_model()


def create_user(email, role, **extra_fields):
    return User.objects.create_user(
        username=email,
        email=email,
        password="StrongPass123!",
        role=role,
        **extra_fields,
    )


def create_provider(email="doctor@example.com"):
    doctor = create_user(email, User.Roles.DOCTOR)
    return Provider.objects.create(
        user=doctor,
        specialization="Cardiology",
        medical_license_number=f"LIC-{doctor.id}",
        experience_years=9,
        consultation_fee="150.00",
        is_verified=True,
    )


def create_appointment(patient, provider, **overrides):
    values = {
        "appointment_date": timezone.localdate() + timedelta(days=2),
        "appointment_time": time(9, 30),
        "status": Appointment.Status.PENDING,
    }
    values.update(overrides)
    return Appointment.objects.create(
        patient=patient,
        provider=provider,
        **values,
    )


def detail_url(appointment):
    return reverse(
        "api_v1:appointments:appointment-detail",
        kwargs={"pk": appointment.pk},
    )


def patch_as(client, user, appointment, payload):
    client.force_authenticate(user=user)
    return client.patch(detail_url(appointment), payload, format="json")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("initial_status", "new_status", "is_past"),
    [
        (Appointment.Status.PENDING, Appointment.Status.CONFIRMED, False),
        (Appointment.Status.PENDING, Appointment.Status.CANCELLED, False),
        (Appointment.Status.CONFIRMED, Appointment.Status.CANCELLED, False),
        (Appointment.Status.CONFIRMED, Appointment.Status.COMPLETED, True),
    ],
)
def test_allowed_status_transitions(
    api_client,
    initial_status,
    new_status,
    is_past,
):
    admin = create_user("admin@example.com", User.Roles.ADMIN)
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    provider = create_provider()
    schedule = (
        {"appointment_date": timezone.localdate() - timedelta(days=1)}
        if is_past
        else {}
    )
    appointment = create_appointment(
        patient,
        provider,
        status=initial_status,
        **schedule,
    )

    response = patch_as(
        api_client,
        admin,
        appointment,
        {"status": new_status},
    )

    appointment.refresh_from_db()
    assert response.status_code == 200
    assert appointment.status == new_status


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("initial_status", "new_status"),
    [
        (Appointment.Status.PENDING, Appointment.Status.COMPLETED),
        (Appointment.Status.CONFIRMED, Appointment.Status.PENDING),
        (Appointment.Status.CANCELLED, Appointment.Status.PENDING),
        (Appointment.Status.CANCELLED, Appointment.Status.CONFIRMED),
        (Appointment.Status.CANCELLED, Appointment.Status.COMPLETED),
        (Appointment.Status.COMPLETED, Appointment.Status.PENDING),
        (Appointment.Status.COMPLETED, Appointment.Status.CONFIRMED),
        (Appointment.Status.COMPLETED, Appointment.Status.CANCELLED),
    ],
)
def test_invalid_status_transitions_return_stable_validation_error(
    api_client,
    initial_status,
    new_status,
):
    admin = create_user("admin@example.com", User.Roles.ADMIN)
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    provider = create_provider()
    appointment = create_appointment(
        patient,
        provider,
        appointment_date=timezone.localdate() - timedelta(days=1),
        status=initial_status,
    )

    response = patch_as(
        api_client,
        admin,
        appointment,
        {"status": new_status},
    )

    appointment.refresh_from_db()
    assert response.status_code == 400
    assert response.json() == {
        "status": [f"Transition from {initial_status} to {new_status} is not allowed."]
    }
    assert appointment.status == initial_status


@pytest.mark.django_db
def test_future_confirmed_appointment_cannot_be_completed(api_client):
    admin = create_user("admin@example.com", User.Roles.ADMIN)
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    provider = create_provider()
    appointment = create_appointment(
        patient,
        provider,
        status=Appointment.Status.CONFIRMED,
    )

    response = patch_as(
        api_client,
        admin,
        appointment,
        {"status": Appointment.Status.COMPLETED},
    )

    appointment.refresh_from_db()
    assert response.status_code == 400
    assert response.json() == {"status": [services.FUTURE_COMPLETION_MESSAGE]}
    assert appointment.status == Appointment.Status.CONFIRMED


@pytest.mark.django_db
def test_same_status_patch_is_an_idempotent_no_op(api_client):
    admin = create_user("admin@example.com", User.Roles.ADMIN)
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    provider = create_provider()
    appointment = create_appointment(patient, provider)
    original_updated_at = appointment.updated_at

    response = patch_as(
        api_client,
        admin,
        appointment,
        {"status": Appointment.Status.PENDING},
    )

    appointment.refresh_from_db()
    assert response.status_code == 200
    assert appointment.status == Appointment.Status.PENDING
    assert appointment.updated_at == original_updated_at


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status",
    [Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
)
def test_admin_can_reschedule_active_appointment(api_client, status):
    admin = create_user("admin@example.com", User.Roles.ADMIN)
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    provider = create_provider()
    appointment = create_appointment(patient, provider, status=status)
    new_date = timezone.localdate() + timedelta(days=4)

    response = patch_as(
        api_client,
        admin,
        appointment,
        {"appointment_date": new_date, "appointment_time": "14:30:00"},
    )

    appointment.refresh_from_db()
    assert response.status_code == 200
    assert appointment.appointment_date == new_date
    assert appointment.appointment_time == time(14, 30)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "status",
    [Appointment.Status.CANCELLED, Appointment.Status.COMPLETED],
)
def test_terminal_appointment_cannot_be_rescheduled(api_client, status):
    admin = create_user("admin@example.com", User.Roles.ADMIN)
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    provider = create_provider()
    appointment = create_appointment(
        patient,
        provider,
        appointment_date=timezone.localdate() - timedelta(days=1),
        status=status,
    )

    response = patch_as(
        api_client,
        admin,
        appointment,
        {
            "appointment_date": timezone.localdate() + timedelta(days=3),
            "appointment_time": "14:30:00",
        },
    )

    appointment.refresh_from_db()
    assert response.status_code == 400
    assert response.json() == {
        "non_field_errors": [services.TERMINAL_RESCHEDULE_MESSAGE]
    }


@pytest.mark.django_db
def test_rescheduling_to_active_slot_returns_stable_400(api_client):
    admin = create_user("admin@example.com", User.Roles.ADMIN)
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    provider = create_provider()
    destination = create_appointment(
        patient,
        provider,
        appointment_time=time(14, 30),
    )
    source = create_appointment(
        patient,
        provider,
        appointment_time=time(15, 30),
    )

    response = patch_as(
        api_client,
        admin,
        source,
        {
            "appointment_date": destination.appointment_date,
            "appointment_time": destination.appointment_time,
        },
    )

    source.refresh_from_db()
    assert response.status_code == 400
    assert response.json() == {"non_field_errors": [services.SLOT_CONFLICT_MESSAGE]}
    assert source.appointment_time == time(15, 30)


@pytest.mark.django_db
def test_rescheduling_to_cancelled_historical_slot_succeeds(api_client):
    admin = create_user("admin@example.com", User.Roles.ADMIN)
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    provider = create_provider()
    cancelled = create_appointment(
        patient,
        provider,
        appointment_time=time(14, 30),
        status=Appointment.Status.CANCELLED,
    )
    source = create_appointment(
        patient,
        provider,
        appointment_time=time(15, 30),
    )

    response = patch_as(
        api_client,
        admin,
        source,
        {
            "appointment_date": cancelled.appointment_date,
            "appointment_time": cancelled.appointment_time,
        },
    )

    source.refresh_from_db()
    cancelled.refresh_from_db()
    assert response.status_code == 200
    assert source.appointment_time == cancelled.appointment_time
    assert cancelled.status == Appointment.Status.CANCELLED


@pytest.mark.django_db
def test_cancelled_slot_can_be_rebooked_and_history_is_preserved(api_client):
    admin = create_user("admin@example.com", User.Roles.ADMIN)
    first_patient = create_user("first@example.com", User.Roles.PATIENT)
    second_patient = create_user("second@example.com", User.Roles.PATIENT)
    provider = create_provider()
    original = create_appointment(first_patient, provider)

    cancel_response = patch_as(
        api_client,
        admin,
        original,
        {"status": Appointment.Status.CANCELLED},
    )
    api_client.force_authenticate(user=second_patient)
    booking_response = api_client.post(
        reverse("api_v1:appointments:appointment-list"),
        {
            "provider": provider.pk,
            "appointment_date": original.appointment_date,
            "appointment_time": original.appointment_time,
        },
        format="json",
    )

    original.refresh_from_db()
    assert cancel_response.status_code == 200
    assert booking_response.status_code == 201
    assert original.status == Appointment.Status.CANCELLED
    assert Appointment.objects.filter(pk=original.pk).exists()
    assert (
        Appointment.objects.filter(
            provider=provider,
            appointment_date=original.appointment_date,
            appointment_time=original.appointment_time,
        ).count()
        == 2
    )


@pytest.mark.django_db
def test_doctor_still_cannot_reschedule(api_client):
    provider = create_provider()
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    appointment = create_appointment(patient, provider)

    response = patch_as(
        api_client,
        provider.user,
        appointment,
        {"appointment_time": "14:30:00"},
    )

    appointment.refresh_from_db()
    assert response.status_code == 403
    assert appointment.appointment_time == time(9, 30)


@pytest.mark.django_db
def test_superuser_retains_reschedule_permission(api_client):
    superuser = User.objects.create_superuser(
        username="root@example.com",
        email="root@example.com",
        password="StrongPass123!",
    )
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    provider = create_provider()
    appointment = create_appointment(patient, provider)

    response = patch_as(
        api_client,
        superuser,
        appointment,
        {"appointment_time": "14:30:00"},
    )

    appointment.refresh_from_db()
    assert response.status_code == 200
    assert appointment.appointment_time == time(14, 30)


@pytest.mark.django_db(transaction=True)
def test_concurrent_reuse_of_cancelled_slot_has_one_active_winner(monkeypatch):
    first_patient = create_user("first@example.com", User.Roles.PATIENT)
    second_patient = create_user("second@example.com", User.Roles.PATIENT)
    historical_patient = create_user("historical@example.com", User.Roles.PATIENT)
    provider = create_provider()
    cancelled = create_appointment(
        historical_patient,
        provider,
        status=Appointment.Status.CANCELLED,
    )
    barrier = Barrier(2)
    original_check = services.active_slot_is_taken

    def synchronized_slot_check(**kwargs):
        result = original_check(**kwargs)
        barrier.wait(timeout=10)
        return result

    monkeypatch.setattr(services, "active_slot_is_taken", synchronized_slot_check)
    payload = {
        "provider": provider.pk,
        "appointment_date": cancelled.appointment_date,
        "appointment_time": cancelled.appointment_time,
    }

    def book(patient):
        connections.close_all()
        client = APIClient()
        client.force_authenticate(user=patient)
        response = client.post(
            reverse("api_v1:appointments:appointment-list"),
            payload,
            format="json",
        )
        connections.close_all()
        return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(book, (first_patient, second_patient)))

    assert sorted(status for status, _ in results) == [201, 400]
    failure = next(body for status, body in results if status == 400)
    assert failure == {"non_field_errors": [services.SLOT_CONFLICT_MESSAGE]}
    slot_rows = Appointment.objects.filter(
        provider=provider,
        appointment_date=cancelled.appointment_date,
        appointment_time=cancelled.appointment_time,
    )
    assert slot_rows.count() == 2
    assert slot_rows.exclude(status=Appointment.Status.CANCELLED).count() == 1
    assert slot_rows.filter(pk=cancelled.pk).exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_reschedules_have_one_active_winner_and_stable_400(monkeypatch):
    admin = create_user("admin@example.com", User.Roles.ADMIN)
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    provider = create_provider()
    first = create_appointment(patient, provider, appointment_time=time(9, 30))
    second = create_appointment(patient, provider, appointment_time=time(10, 30))
    destination_time = time(14, 30)
    barrier = Barrier(2)
    original_check = services.active_slot_is_taken

    def synchronized_slot_check(**kwargs):
        result = original_check(**kwargs)
        barrier.wait(timeout=10)
        return result

    monkeypatch.setattr(services, "active_slot_is_taken", synchronized_slot_check)

    def reschedule(appointment):
        connections.close_all()
        client = APIClient()
        client.force_authenticate(user=admin)
        response = client.patch(
            detail_url(appointment),
            {"appointment_time": destination_time},
            format="json",
        )
        connections.close_all()
        return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(reschedule, (first, second)))

    assert sorted(status for status, _ in results) == [200, 400]
    failure = next(body for status, body in results if status == 400)
    assert failure == {"non_field_errors": [services.SLOT_CONFLICT_MESSAGE]}
    assert (
        Appointment.objects.exclude(status=Appointment.Status.CANCELLED)
        .filter(
            provider=provider,
            appointment_date=first.appointment_date,
            appointment_time=destination_time,
        )
        .count()
        == 1
    )
