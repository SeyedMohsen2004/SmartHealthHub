"""Project-level API views."""
from django.db import connection
from django.db.utils import OperationalError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """Expose a lightweight readiness endpoint for containers and load balancers."""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        database_status = "ok"
        response_status = status.HTTP_200_OK

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except OperationalError:
            database_status = "unavailable"
            response_status = status.HTTP_503_SERVICE_UNAVAILABLE

        return Response(
            {
                "status": "ok" if response_status == status.HTTP_200_OK else "error",
                "database": database_status,
            },
            status=response_status,
        )
