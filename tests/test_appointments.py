from datetime import time, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

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


def create_provider(email="doctor@example.com", specialization="Cardiology"):
    doctor = create_user(
        email,
        User.Roles.DOCTOR,
        first_name="Dana",
        last_name="Care",
    )
    return Provider.objects.create(
        user=doctor,
        specialization=specialization,
        medical_license_number=f"LIC-{doctor.id}",
        experience_years=9,
        bio="Experienced specialist.",
        consultation_fee="150.00",
        is_verified=True,
    )


def appointment_payload(provider, **overrides):
    payload = {
        "provider": provider.id,
        "appointment_date": timezone.localdate() + timedelta(days=1),
        "appointment_time": "09:30:00",
    }
    payload.update(overrides)
    return payload


def create_appointment(patient, provider, **overrides):
    defaults = {
        "appointment_date": timezone.localdate() + timedelta(days=1),
        "appointment_time": time(9, 30),
        "status": Appointment.Status.PENDING,
    }
    defaults.update(overrides)
    return Appointment.objects.create(
        patient=patient,
        provider=provider,
        **defaults,
    )


@pytest.mark.django_db
def test_patient_can_create_appointment(api_client):
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    provider = create_provider()
    api_client.force_authenticate(user=patient)

    response = api_client.post(
        reverse("api_v1:appointments:appointment-list"),
        appointment_payload(provider),
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["patient"] == patient.id
    assert response.json()["provider"] == provider.id
    assert response.json()["status"] == Appointment.Status.PENDING


@pytest.mark.django_db
def test_unauthenticated_user_denied(api_client):
    response = api_client.get(reverse("api_v1:appointments:appointment-list"))

    assert response.status_code == 401


@pytest.mark.django_db
def test_patient_sees_only_own_appointments(api_client):
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    other_patient = create_user("other@example.com", User.Roles.PATIENT)
    provider = create_provider()
    own_appointment = create_appointment(patient, provider)
    create_appointment(
        other_patient,
        provider,
        appointment_time=time(10, 30),
    )
    api_client.force_authenticate(user=patient)

    response = api_client.get(reverse("api_v1:appointments:appointment-list"))

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["results"]] == [own_appointment.id]


@pytest.mark.django_db
def test_doctor_sees_assigned_provider_appointments(api_client):
    provider = create_provider("assigned@example.com", "Cardiology")
    other_provider = create_provider("other-doctor@example.com", "Dermatology")
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    assigned = create_appointment(patient, provider)
    create_appointment(patient, other_provider, appointment_time=time(11, 30))
    api_client.force_authenticate(user=provider.user)

    response = api_client.get(reverse("api_v1:appointments:appointment-list"))

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["results"]] == [assigned.id]


@pytest.mark.django_db
def test_admin_sees_all_appointments(api_client):
    admin = create_user("admin@example.com", User.Roles.ADMIN)
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    provider = create_provider()
    create_appointment(patient, provider)
    create_appointment(patient, provider, appointment_time=time(12, 30))
    api_client.force_authenticate(user=admin)

    response = api_client.get(reverse("api_v1:appointments:appointment-list"))

    assert response.status_code == 200
    assert response.json()["count"] == 2


@pytest.mark.django_db
def test_duplicate_appointment_rejected(api_client):
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    other_patient = create_user("other@example.com", User.Roles.PATIENT)
    provider = create_provider()
    appointment_date = timezone.localdate() + timedelta(days=1)
    create_appointment(
        other_patient,
        provider,
        appointment_date=appointment_date,
        appointment_time=time(9, 30),
    )
    api_client.force_authenticate(user=patient)

    response = api_client.post(
        reverse("api_v1:appointments:appointment-list"),
        appointment_payload(provider, appointment_date=appointment_date),
        format="json",
    )

    assert response.status_code == 400
    assert "already has an appointment" in str(response.json())


@pytest.mark.django_db
def test_appointment_date_cannot_be_in_past(api_client):
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    provider = create_provider()
    api_client.force_authenticate(user=patient)

    response = api_client.post(
        reverse("api_v1:appointments:appointment-list"),
        appointment_payload(
            provider,
            appointment_date=timezone.localdate() - timedelta(days=1),
        ),
        format="json",
    )

    assert response.status_code == 400
    assert "appointment_date" in response.json()


@pytest.mark.django_db
def test_admin_can_update_appointment_status(api_client):
    admin = create_user("admin@example.com", User.Roles.ADMIN)
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    provider = create_provider()
    appointment = create_appointment(patient, provider)
    api_client.force_authenticate(user=admin)

    response = api_client.patch(
        reverse(
            "api_v1:appointments:appointment-detail",
            kwargs={"pk": appointment.id},
        ),
        {"status": Appointment.Status.CONFIRMED},
        format="json",
    )

    appointment.refresh_from_db()
    assert response.status_code == 200
    assert appointment.status == Appointment.Status.CONFIRMED


@pytest.mark.django_db
def test_doctor_can_update_own_appointment_status(api_client):
    provider = create_provider("doctor@example.com", "Cardiology")
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    appointment = create_appointment(patient, provider)
    api_client.force_authenticate(user=provider.user)

    response = api_client.patch(
        reverse(
            "api_v1:appointments:appointment-detail",
            kwargs={"pk": appointment.id},
        ),
        {"status": Appointment.Status.CONFIRMED},
        format="json",
    )

    appointment.refresh_from_db()
    assert response.status_code == 200
    assert appointment.status == Appointment.Status.CONFIRMED


@pytest.mark.django_db
def test_doctor_cannot_update_another_doctors_appointment(api_client):
    provider = create_provider("doctor@example.com", "Cardiology")
    other_provider = create_provider("other-doctor@example.com", "Neurology")
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    appointment = create_appointment(patient, other_provider)
    api_client.force_authenticate(user=provider.user)

    response = api_client.patch(
        reverse(
            "api_v1:appointments:appointment-detail",
            kwargs={"pk": appointment.id},
        ),
        {"status": Appointment.Status.CONFIRMED},
        format="json",
    )

    appointment.refresh_from_db()
    assert response.status_code == 403
    assert appointment.status == Appointment.Status.PENDING


@pytest.mark.django_db
def test_patient_cannot_update_appointment(api_client):
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    provider = create_provider()
    appointment = create_appointment(patient, provider)
    api_client.force_authenticate(user=patient)

    response = api_client.patch(
        reverse(
            "api_v1:appointments:appointment-detail",
            kwargs={"pk": appointment.id},
        ),
        {"status": Appointment.Status.CANCELLED},
        format="json",
    )

    appointment.refresh_from_db()
    assert response.status_code == 403
    assert appointment.status == Appointment.Status.PENDING


@pytest.mark.django_db
def test_admin_can_delete_appointment(api_client):
    admin = create_user("admin@example.com", User.Roles.ADMIN)
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    provider = create_provider()
    appointment = create_appointment(patient, provider)
    api_client.force_authenticate(user=admin)

    response = api_client.delete(
        reverse(
            "api_v1:appointments:appointment-detail",
            kwargs={"pk": appointment.id},
        )
    )

    assert response.status_code == 204
    assert not Appointment.objects.filter(id=appointment.id).exists()


@pytest.mark.django_db
def test_filter_appointments(api_client):
    admin = create_user("admin@example.com", User.Roles.ADMIN)
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    provider = create_provider()
    appointment_date = timezone.localdate() + timedelta(days=2)
    expected = create_appointment(
        patient,
        provider,
        appointment_date=appointment_date,
        status=Appointment.Status.CONFIRMED,
    )
    create_appointment(
        patient,
        provider,
        appointment_date=timezone.localdate() + timedelta(days=3),
        appointment_time=time(13, 30),
        status=Appointment.Status.CANCELLED,
    )
    api_client.force_authenticate(user=admin)

    response = api_client.get(
        reverse("api_v1:appointments:appointment-list"),
        {
            "status": Appointment.Status.CONFIRMED,
            "provider": provider.id,
            "appointment_date": appointment_date,
        },
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["results"]] == [expected.id]


@pytest.mark.django_db
def test_search_appointments(api_client):
    admin = create_user("admin@example.com", User.Roles.ADMIN)
    patient = create_user("search-patient@example.com", User.Roles.PATIENT)
    provider = create_provider(specialization="Neurology")
    expected = create_appointment(patient, provider)
    api_client.force_authenticate(user=admin)

    response = api_client.get(
        reverse("api_v1:appointments:appointment-list"),
        {"search": "Neurology"},
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["results"]] == [expected.id]
