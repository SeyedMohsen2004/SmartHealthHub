"""Appointments API URLs."""

from rest_framework.routers import DefaultRouter

from appointments.views import AppointmentViewSet

app_name = "appointments"

router = DefaultRouter()
router.register("", AppointmentViewSet, basename="appointment")

urlpatterns = router.urls
