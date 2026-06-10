"""Providers API URLs."""

from rest_framework.routers import DefaultRouter

from providers.views import ProviderViewSet

app_name = "providers"

router = DefaultRouter()
router.register("", ProviderViewSet, basename="provider")

urlpatterns = router.urls
