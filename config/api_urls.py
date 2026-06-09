"""Versioned API URL configuration."""
from django.urls import include, path

from config.views import HealthCheckView

app_name = "api_v1"

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path(
        "auth/",
        include(("accounts.urls", "accounts"), namespace="accounts"),
    ),
    path("providers/", include("providers.urls")),
    path("appointments/", include("appointments.urls")),
    path("notifications/", include("notifications.urls")),
]
