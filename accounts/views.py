"""API views for accounts."""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.serializers import (
    LoginSerializer,
    LogoutSerializer,
    RefreshRequestSerializer,
    RefreshSerializer,
    RegisterSerializer,
    TokenPairSerializer,
    UserProfileSerializer,
)

THROTTLED_RESPONSE = OpenApiResponse(
    description="Request rate exceeded. A Retry-After header may be included."
)


@extend_schema(
    tags=["Accounts"],
    request=RegisterSerializer,
    responses={
        status.HTTP_201_CREATED: RegisterSerializer,
        status.HTTP_429_TOO_MANY_REQUESTS: THROTTLED_RESPONSE,
    },
)
class RegisterAPIView(generics.CreateAPIView):
    """Create a patient account and return JWT tokens."""

    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer
    throttle_scope = "auth_register"

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
    responses={
        status.HTTP_200_OK: LoginSerializer,
        status.HTTP_429_TOO_MANY_REQUESTS: THROTTLED_RESPONSE,
    },
)
class LoginAPIView(generics.GenericAPIView):
    """Authenticate with email and password."""

    permission_classes = (permissions.AllowAny,)
    serializer_class = LoginSerializer
    throttle_scope = "auth_login"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


@extend_schema(
    tags=["Accounts"],
    request=RefreshRequestSerializer,
    responses={
        status.HTTP_200_OK: TokenPairSerializer,
        status.HTTP_429_TOO_MANY_REQUESTS: THROTTLED_RESPONSE,
    },
)
class RefreshAPIView(TokenRefreshView):
    """Rotate a refresh token and return a new token pair."""

    permission_classes = (permissions.AllowAny,)
    serializer_class = RefreshSerializer
    throttle_scope = "auth_refresh"


@extend_schema(
    tags=["Accounts"],
    request=LogoutSerializer,
    responses={
        status.HTTP_204_NO_CONTENT: None,
        status.HTTP_400_BAD_REQUEST: OpenApiResponse(
            description="The refresh token is invalid, expired, or already revoked."
        ),
        status.HTTP_429_TOO_MANY_REQUESTS: THROTTLED_RESPONSE,
    },
)
class LogoutAPIView(generics.GenericAPIView):
    """Revoke one refresh token while leaving access tokens stateless."""

    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)
    serializer_class = LogoutSerializer
    throttle_scope = "auth_logout"

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


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
