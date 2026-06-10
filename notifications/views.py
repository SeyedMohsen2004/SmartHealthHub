"""API views for notifications."""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets

from notifications.models import Notification
from notifications.serializers import NotificationSerializer


@extend_schema_view(
    list=extend_schema(tags=["Notifications"]),
    retrieve=extend_schema(tags=["Notifications"]),
    partial_update=extend_schema(tags=["Notifications"]),
)
class NotificationViewSet(viewsets.ModelViewSet):
    """Manage user notifications."""

    serializer_class = NotificationSerializer
    permission_classes = (permissions.IsAuthenticated,)
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user

        queryset = Notification.objects.select_related("user")

        if user.is_superuser or user.role == user.Roles.ADMIN:
            return queryset

        return queryset.filter(user=user)
