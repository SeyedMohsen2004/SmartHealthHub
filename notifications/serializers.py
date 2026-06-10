"""Serializers for notifications."""

from rest_framework import serializers

from notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Serialize notifications."""

    class Meta:
        model = Notification
        fields = (
            "id",
            "title",
            "message",
            "is_read",
            "created_at",
        )
        read_only_fields = (
            "id",
            "title",
            "message",
            "created_at",
        )
