"""Serializers for accounts."""

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError, transaction
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class TokenPairSerializer(serializers.Serializer):
    """Document the access and refresh tokens returned at registration."""

    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


class UserProfileSerializer(serializers.ModelSerializer):
    """Serialize authenticated user profile data."""

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "role",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "username",
            "email",
            "role",
            "created_at",
            "updated_at",
        )

    def validate_phone_number(self, value):
        if value and not value.replace("+", "", 1).replace("-", "").isdigit():
            raise serializers.ValidationError("Enter a valid phone number.")
        return value


class RegisterSerializer(serializers.ModelSerializer):
    """Validate and create user accounts."""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    tokens = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "phone_number",
            "role",
            "created_at",
            "updated_at",
            "tokens",
        )
        read_only_fields = ("id", "role", "created_at", "updated_at", "tokens")
        extra_kwargs = {
            "username": {"required": False, "allow_blank": True},
            "email": {"required": True},
        }

    def validate_email(self, value):
        email = value.lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_phone_number(self, value):
        if value and not value.replace("+", "", 1).replace("-", "").isdigit():
            raise serializers.ValidationError("Enter a valid phone number.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        email = validated_data["email"]

        if not validated_data.get("username"):
            validated_data["username"] = email

        try:
            user = User(**validated_data)
            user.set_password(password)
            user.save()
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"email": "A user with this email already exists."}
            ) from exc

        return user

    @extend_schema_field(TokenPairSerializer)
    def get_tokens(self, obj):
        refresh = RefreshToken.for_user(obj)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }


class LoginSerializer(serializers.Serializer):
    """Authenticate a user by email and return JWT tokens."""

    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    def validate(self, attrs):
        email = attrs["email"].lower().strip()
        password = attrs["password"]

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"detail": "Unable to log in with provided credentials."}
            ) from exc

        authenticated_user = authenticate(
            request=self.context.get("request"),
            username=user.get_username(),
            password=password,
        )

        if authenticated_user is None:
            raise serializers.ValidationError(
                {"detail": "Unable to log in with provided credentials."}
            )

        if not authenticated_user.is_active:
            raise serializers.ValidationError({"detail": "User account is disabled."})

        refresh = RefreshToken.for_user(authenticated_user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


class RefreshSerializer(TokenRefreshSerializer):
    """Refresh JWT access tokens."""
