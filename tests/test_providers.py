import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

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


def provider_payload(user, **overrides):
    payload = {
        "user": user.id,
        "specialization": "Cardiology",
        "medical_license_number": f"LIC-{user.id}",
        "experience_years": 8,
        "bio": "Board-certified specialist.",
        "consultation_fee": "150.00",
        "is_verified": True,
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_authenticated_user_can_list_providers(api_client):
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    doctor = create_user(
        "doctor@example.com",
        User.Roles.DOCTOR,
        first_name="Dana",
        last_name="Care",
    )
    Provider.objects.create(
        user=doctor,
        specialization="Cardiology",
        medical_license_number="CARD-001",
        experience_years=10,
        bio="Heart specialist.",
        consultation_fee="200.00",
        is_verified=True,
    )
    api_client.force_authenticate(user=patient)

    response = api_client.get(reverse("api_v1:providers:provider-list"))

    assert response.status_code == 200
    assert response.json()["results"][0]["specialization"] == "Cardiology"


@pytest.mark.django_db
def test_unauthenticated_user_cannot_list_providers(api_client):
    response = api_client.get(reverse("api_v1:providers:provider-list"))

    assert response.status_code == 401


@pytest.mark.django_db
def test_admin_can_create_provider(api_client):
    admin = create_user("admin@example.com", User.Roles.ADMIN)
    doctor = create_user("create-doctor@example.com", User.Roles.DOCTOR)
    api_client.force_authenticate(user=admin)

    response = api_client.post(
        reverse("api_v1:providers:provider-list"),
        provider_payload(doctor),
        format="json",
    )

    assert response.status_code == 201
    assert Provider.objects.filter(user=doctor).exists()
    assert response.json()["medical_license_number"] == f"LIC-{doctor.id}"


@pytest.mark.django_db
def test_non_admin_cannot_create_provider(api_client):
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    doctor = create_user("blocked-doctor@example.com", User.Roles.DOCTOR)
    api_client.force_authenticate(user=patient)

    response = api_client.post(
        reverse("api_v1:providers:provider-list"),
        provider_payload(doctor),
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_provider_must_be_linked_to_doctor_user(api_client):
    admin = create_user("admin@example.com", User.Roles.ADMIN)
    patient = create_user("not-doctor@example.com", User.Roles.PATIENT)
    api_client.force_authenticate(user=admin)

    response = api_client.post(
        reverse("api_v1:providers:provider-list"),
        provider_payload(patient),
        format="json",
    )

    assert response.status_code == 400
    assert "user" in response.json()


@pytest.mark.django_db
def test_admin_can_update_provider(api_client):
    admin = create_user("admin@example.com", User.Roles.ADMIN)
    doctor = create_user("patch-doctor@example.com", User.Roles.DOCTOR)
    provider = Provider.objects.create(
        user=doctor,
        specialization="General Medicine",
        medical_license_number="GEN-001",
        experience_years=3,
        bio="Primary care.",
        consultation_fee="90.00",
    )
    api_client.force_authenticate(user=admin)

    response = api_client.patch(
        reverse("api_v1:providers:provider-detail", kwargs={"pk": provider.id}),
        {"specialization": "Family Medicine", "is_verified": True},
        format="json",
    )

    provider.refresh_from_db()
    assert response.status_code == 200
    assert provider.specialization == "Family Medicine"
    assert provider.is_verified is True


@pytest.mark.django_db
def test_admin_can_delete_provider(api_client):
    admin = create_user("admin@example.com", User.Roles.ADMIN)
    doctor = create_user("delete-doctor@example.com", User.Roles.DOCTOR)
    provider = Provider.objects.create(
        user=doctor,
        specialization="Dermatology",
        medical_license_number="DERM-001",
        experience_years=7,
        bio="Skin specialist.",
        consultation_fee="120.00",
    )
    api_client.force_authenticate(user=admin)

    response = api_client.delete(
        reverse("api_v1:providers:provider-detail", kwargs={"pk": provider.id})
    )

    assert response.status_code == 204
    assert not Provider.objects.filter(id=provider.id).exists()


@pytest.mark.django_db
def test_filter_and_search_providers(api_client):
    patient = create_user("patient@example.com", User.Roles.PATIENT)
    cardiologist = create_user(
        "cardio@example.com",
        User.Roles.DOCTOR,
        first_name="Clara",
        last_name="Heart",
    )
    dermatologist = create_user(
        "derm@example.com",
        User.Roles.DOCTOR,
        first_name="Nima",
        last_name="Skin",
    )
    Provider.objects.create(
        user=cardiologist,
        specialization="Cardiology",
        medical_license_number="CARD-001",
        experience_years=11,
        bio="Heart specialist.",
        consultation_fee="210.00",
        is_verified=True,
    )
    Provider.objects.create(
        user=dermatologist,
        specialization="Dermatology",
        medical_license_number="DERM-001",
        experience_years=6,
        bio="Skin specialist.",
        consultation_fee="160.00",
        is_verified=False,
    )
    api_client.force_authenticate(user=patient)

    response = api_client.get(
        reverse("api_v1:providers:provider-list"),
        {"specialization": "Cardiology", "is_verified": "true", "search": "Clara"},
    )

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["first_name"] == "Clara"
