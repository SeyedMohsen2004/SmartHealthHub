# Appointment reminders

SmartHealthHub creates in-app appointment reminders through periodic database
reconciliation:

```text
PostgreSQL appointment state
        -> Celery Beat scan
        -> Redis broker
        -> Celery worker
        -> PostgreSQL Notification row
```

PostgreSQL is the durable business source of truth. Redis carries short-lived
dispatcher messages; it does not decide whether a reminder should exist. A
Redis restart, worker outage, or Beat outage therefore cannot erase future
reminder intent. Once dispatch resumes, any eligible future appointment still
inside the reminder window is reconciled.

## Policy

- Lead time: `24` hours by default.
- Scan interval: `60` seconds by default.
- Eligible states: `PENDING` and `CONFIRMED`.
- Ineligible states: `CANCELLED`, `COMPLETED`, and past appointments.
- An appointment created with less than 24 hours remaining is picked up by the
  next scan.

The settings are configurable with `APPOINTMENT_REMINDER_LEAD_HOURS`,
`APPOINTMENT_REMINDER_SCAN_INTERVAL_SECONDS`, and
`APPOINTMENT_REMINDER_BATCH_SIZE`. `CELERY_BROKER_URL` selects the broker.

## Reconciliation and idempotency

Beat enqueues one bounded dispatcher task per scan, not one long-lived task per
appointment. The dispatcher selects plausible candidates with indexed schedule
fields, then handles each appointment in its own short transaction. It locks
and re-reads that appointment, revalidates status and its current aware schedule,
and creates an in-app notification only if it remains due.

Appointment-specific ETA/countdown tasks are intentionally avoided: schedules
can move or be cancelled, Redis is not the business source of truth, long ETA
messages complicate broker recovery, and periodic PostgreSQL reconciliation
naturally catches up after downtime.

Each reminder stores its appointment and the scheduled-datetime snapshot that
caused it. A conditional database constraint permits at most one
`APPOINTMENT_REMINDER` for an appointment and snapshot. Repeated task delivery
and concurrent dispatcher runs are therefore safe; application checks provide
an efficient fast path, while PostgreSQL remains the final duplicate barrier.
Generic notifications are unaffected.

If an appointment moves before its reminder is created, only the current
schedule can generate a reminder. If it moves after a reminder was created, the
old reminder remains historical and the new schedule may create exactly one new
reminder when eligible.

## Runtime and operational boundaries

The production topology runs one Beat process and one or more workers from the
same non-root application image as the web service. Only one Beat scheduler may
run for this static schedule. Redis uses append-only persistence and a named
volume to reduce broker-message loss during restarts, but correctness still
comes from PostgreSQL reconciliation.

The task retries only transient database connectivity failures, at most three
times, with bounded exponential backoff and jitter. Ineligible state, malformed
data, and programming errors are not retried indefinitely. Task results are
ignored and no Celery result backend is configured.

This phase delivers only existing in-app `Notification` rows. It does not send
email, SMS, push notifications, or WebSockets. It also does not add notification
preferences, `django-celery-beat`, `django-celery-results`, Flower, clustered
Redis, or monitoring. A single local Redis instance is an intentional bounded
portfolio topology, not a high-availability broker design.
