import pytest
from django.db.utils import OperationalError
from django.urls import reverse


@pytest.mark.django_db
def test_health_check_returns_ok(api_client):
    response = api_client.get(reverse("api_v1:health-check"))

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.django_db
def test_health_check_returns_503_when_database_is_unavailable(api_client, monkeypatch):
    def unavailable_cursor():
        raise OperationalError("database unavailable")

    monkeypatch.setattr("config.views.connection.cursor", unavailable_cursor)

    response = api_client.get(reverse("api_v1:health-check"))

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unavailable"}
