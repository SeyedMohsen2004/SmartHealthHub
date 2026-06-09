import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
def test_register_creates_patient_user_and_returns_tokens(api_client):
    response = api_client.post(
        reverse("api_v1:accounts:register"),
        {
            "email": "patient@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
            "first_name": "Pat",
            "last_name": "Smith",
            "phone_number": "+989123456789",
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "patient@example.com"
    assert body["username"] == "patient@example.com"
    assert body["role"] == "PATIENT"
    assert body["tokens"]["access"]
    assert body["tokens"]["refresh"]
    assert User.objects.filter(email="patient@example.com").exists()


@pytest.mark.django_db
def test_register_rejects_duplicate_email(api_client):
    User.objects.create_user(
        username="existing@example.com",
        email="existing@example.com",
        password="StrongPass123!",
    )

    response = api_client.post(
        reverse("api_v1:accounts:register"),
        {
            "email": "existing@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "email" in response.json()


@pytest.mark.django_db
def test_register_rejects_password_mismatch(api_client):
    response = api_client.post(
        reverse("api_v1:accounts:register"),
        {
            "email": "patient@example.com",
            "password": "StrongPass123!",
            "password_confirm": "DifferentPass123!",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "password_confirm" in response.json()


@pytest.mark.django_db
def test_login_returns_jwt_tokens(api_client):
    User.objects.create_user(
        username="doctor@example.com",
        email="doctor@example.com",
        password="StrongPass123!",
    )

    response = api_client.post(
        reverse("api_v1:accounts:login"),
        {"email": "doctor@example.com", "password": "StrongPass123!"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["access"]
    assert response.json()["refresh"]


@pytest.mark.django_db
def test_refresh_returns_new_access_token(api_client):
    login_response = api_client.post(
        reverse("api_v1:accounts:register"),
        {
            "email": "refresh@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        },
        format="json",
    )
    refresh_token = login_response.json()["tokens"]["refresh"]

    response = api_client.post(
        reverse("api_v1:accounts:refresh"),
        {"refresh": refresh_token},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["access"]


@pytest.mark.django_db
def test_profile_requires_authentication(api_client):
    response = api_client.get(reverse("api_v1:accounts:profile"))

    assert response.status_code == 401


@pytest.mark.django_db
def test_get_profile_returns_authenticated_user(api_client):
    user = User.objects.create_user(
        username="profile@example.com",
        email="profile@example.com",
        password="StrongPass123!",
        first_name="Profile",
    )
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("api_v1:accounts:profile"))

    assert response.status_code == 200
    assert response.json()["email"] == "profile@example.com"
    assert response.json()["first_name"] == "Profile"


@pytest.mark.django_db
def test_patch_profile_updates_allowed_fields(api_client):
    user = User.objects.create_user(
        username="update@example.com",
        email="update@example.com",
        password="StrongPass123!",
    )
    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse("api_v1:accounts:profile"),
        {
            "first_name": "Updated",
            "phone_number": "+989123456789",
            "role": "ADMIN",
        },
        format="json",
    )

    user.refresh_from_db()
    assert response.status_code == 200
    assert user.first_name == "Updated"
    assert user.phone_number == "+989123456789"
    assert user.role == "PATIENT"
