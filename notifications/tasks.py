"""Thin Celery wrappers for notification-domain services."""

from celery import shared_task
from django.db import OperationalError

from notifications.services import dispatch_due_appointment_reminders as dispatch


@shared_task(
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
    ignore_result=True,
)
def dispatch_due_appointment_reminders():
    """Run one bounded PostgreSQL reminder reconciliation scan."""

    return dispatch()
