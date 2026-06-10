"""API views for accounts."""

from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.serializers import (
    LoginSerializer,
    RefreshSerializer,
    RegisterSerializer,
    UserProfileSerializer,
)


@extend_schema(
    tags=["Accounts"],
    request=RegisterSerializer,
    responses={status.HTTP_201_CREATED: RegisterSerializer},
)
class RegisterAPIView(generics.CreateAPIView):
    """Create a patient account and return JWT tokens."""

    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        response_serializer = self.get_serializer(user)
        headers = self.get_success_headers(response_serializer.data)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )


@extend_schema(
    tags=["Accounts"],
    request=LoginSerializer,
    responses={status.HTTP_200_OK: LoginSerializer},
)
class LoginAPIView(generics.GenericAPIView):
    """Authenticate with email and password."""

    permission_classes = (permissions.AllowAny,)
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


@extend_schema(tags=["Accounts"], request=RefreshSerializer)
class RefreshAPIView(TokenRefreshView):
    """Refresh an access token."""

    permission_classes = (permissions.AllowAny,)
    serializer_class = RefreshSerializer


@extend_schema(
    tags=["Accounts"],
    request=UserProfileSerializer,
    responses={status.HTTP_200_OK: UserProfileSerializer},
)
class ProfileAPIView(generics.RetrieveUpdateAPIView):
    """Retrieve or partially update the authenticated user's profile."""

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = UserProfileSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user
