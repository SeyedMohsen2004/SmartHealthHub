import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from notifications.models import Notification

User = get_user_model()


def create_user(email, role):
    return User.objects.create_user(
        username=email,
        email=email,
        password="StrongPass123!",
        role=role,
    )


@pytest.mark.django_db
def test_user_can_list_own_notifications(api_client):
    user = create_user("user@example.com", User.Roles.PATIENT)

    Notification.objects.create(
        user=user,
        title="Appointment",
        message="Appointment confirmed",
    )

    api_client.force_authenticate(user=user)

    response = api_client.get(
        reverse("api_v1:notifications:notification-list")
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.django_db
def test_user_cannot_see_other_users_notifications(api_client):
    user1 = create_user("user1@example.com", User.Roles.PATIENT)
    user2 = create_user("user2@example.com", User.Roles.PATIENT)

    Notification.objects.create(
        user=user2,
        title="Private",
        message="Hidden",
    )

    api_client.force_authenticate(user=user1)

    response = api_client.get(
        reverse("api_v1:notifications:notification-list")
    )

    assert response.status_code == 200
    assert len(response.json()) == 0


@pytest.mark.django_db
def test_admin_can_see_all_notifications(api_client):
    admin = create_user("admin@example.com", User.Roles.ADMIN)

    user1 = create_user("u1@example.com", User.Roles.PATIENT)
    user2 = create_user("u2@example.com", User.Roles.PATIENT)

    Notification.objects.create(user=user1, title="A", message="A")
    Notification.objects.create(user=user2, title="B", message="B")

    api_client.force_authenticate(user=admin)

    response = api_client.get(
        reverse("api_v1:notifications:notification-list")
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.django_db
def test_notifications_require_authentication(api_client):
    response = api_client.get(
        reverse("api_v1:notifications:notification-list")
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_user_can_retrieve_notification(api_client):
    user = create_user("user@example.com", User.Roles.PATIENT)

    notification = Notification.objects.create(
        user=user,
        title="Reminder",
        message="Visit tomorrow",
    )

    api_client.force_authenticate(user=user)

    response = api_client.get(
        reverse(
            "api_v1:notifications:notification-detail",
            kwargs={"pk": notification.id},
        )
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Reminder"


@pytest.mark.django_db
def test_user_can_mark_notification_as_read(api_client):
    user = create_user("user@example.com", User.Roles.PATIENT)

    notification = Notification.objects.create(
        user=user,
        title="Reminder",
        message="Visit tomorrow",
        is_read=False,
    )

    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse(
            "api_v1:notifications:notification-detail",
            kwargs={"pk": notification.id},
        ),
        {"is_read": True},
        format="json",
    )

    notification.refresh_from_db()

    assert response.status_code == 200
    assert notification.is_read is True


@pytest.mark.django_db
def test_title_and_message_cannot_be_modified(api_client):
    user = create_user("user@example.com", User.Roles.PATIENT)

    notification = Notification.objects.create(
        user=user,
        title="Original",
        message="Original Message",
    )

    api_client.force_authenticate(user=user)

    response = api_client.patch(
        reverse(
            "api_v1:notifications:notification-detail",
            kwargs={"pk": notification.id},
        ),
        {
            "title": "Changed",
            "message": "Changed Message",
            "is_read": True,
        },
        format="json",
    )

    notification.refresh_from_db()

    assert response.status_code == 200
    assert notification.title == "Original"
    assert notification.message == "Original Message"
    assert notification.is_read is True