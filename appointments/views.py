"""API views for appointments."""

from drf_spectacular.utils import extend_schema, extend_schema_view
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from appointments.models import Appointment
from appointments.serializers import AppointmentCreateSerializer, AppointmentSerializer


class AppointmentPermission(permissions.BasePermission):
    """Authorize appointment access by user role and action."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if view.action == "create":
            return request.user.role == request.user.Roles.PATIENT

        if view.action == "partial_update":
            return (
                request.user.is_superuser
                or request.user.role == request.user.Roles.ADMIN
                or request.user.role == request.user.Roles.DOCTOR
            )

        if view.action == "destroy":
            return (
                request.user.is_superuser
                or request.user.role == request.user.Roles.ADMIN
            )

        return True

    def has_object_permission(self, request, view, obj):
        if view.action == "partial_update":
            if (
                request.user.is_superuser
                or request.user.role == request.user.Roles.ADMIN
            ):
                return True

            return (
                request.user.role == request.user.Roles.DOCTOR
                and obj.provider.user_id == request.user.id
            )

        if view.action == "destroy":
            return (
                request.user.is_superuser
                or request.user.role == request.user.Roles.ADMIN
            )

        return True


@extend_schema_view(
    list=extend_schema(tags=["Appointments"]),
    retrieve=extend_schema(tags=["Appointments"]),
    create=extend_schema(tags=["Appointments"], request=AppointmentCreateSerializer),
    partial_update=extend_schema(tags=["Appointments"]),
    destroy=extend_schema(tags=["Appointments"]),
)
class AppointmentViewSet(viewsets.ModelViewSet):
    """Manage appointments with role-scoped query access."""

    serializer_class = AppointmentSerializer
    permission_classes = (AppointmentPermission,)
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filter_backends = (
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    )
    filterset_fields = ("status", "provider", "appointment_date")
    search_fields = ("patient__email", "provider__specialization")
    ordering_fields = ("appointment_date", "created_at")
    ordering = ("appointment_date", "appointment_time")

    def get_queryset(self):
        user = self.request.user
        queryset = Appointment.objects.select_related("patient", "provider__user")

        if user.is_superuser or user.role == user.Roles.ADMIN:
            return queryset

        if user.role == user.Roles.DOCTOR:
            if self.action == "partial_update":
                return queryset
            return queryset.filter(provider__user=user)

        return queryset.filter(patient=user)

    def get_serializer_class(self):
        if self.action == "create":
            return AppointmentCreateSerializer
        return AppointmentSerializer

    def partial_update(self, request, *args, **kwargs):
        if request.user.role == request.user.Roles.DOCTOR and set(
            request.data.keys()
        ) != {"status"}:
            raise PermissionDenied("Doctors can only update appointment status.")

        return super().partial_update(request, *args, **kwargs)
