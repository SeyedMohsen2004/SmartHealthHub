"""API views for providers."""
from drf_spectacular.utils import extend_schema, extend_schema_view
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets

from providers.models import Provider
from providers.serializers import ProviderSerializer


class IsAdminRoleOrReadOnly(permissions.BasePermission):
    """Allow authenticated reads and restrict writes to admin users."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        return (
            request.user.is_superuser
            or request.user.role == request.user.Roles.ADMIN
        )


@extend_schema_view(
    list=extend_schema(tags=["Providers"]),
    retrieve=extend_schema(tags=["Providers"]),
    create=extend_schema(tags=["Providers"]),
    partial_update=extend_schema(tags=["Providers"]),
    destroy=extend_schema(tags=["Providers"]),
)
class ProviderViewSet(viewsets.ModelViewSet):
    """Manage healthcare provider profiles."""

    queryset = Provider.objects.select_related("user").all()
    serializer_class = ProviderSerializer
    permission_classes = (IsAdminRoleOrReadOnly,)
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filter_backends = (
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    filterset_fields = ("specialization", "is_verified")
    search_fields = ("user__first_name", "user__last_name", "specialization")
    ordering_fields = ("created_at", "experience_years", "consultation_fee")
    ordering = ("-created_at",)
