# Security architecture

This document describes controls that are implemented in the repository. It is
not a compliance claim, penetration-test report, or guarantee of zero risk.

## Authentication and authorization

SmartHealthHub uses short-lived JWT access tokens and seven-day refresh tokens.
SimpleJWT rotates a refresh token after use and blacklists the consumed token.
`POST /api/v1/auth/logout/` revokes only the submitted refresh token. Access
tokens remain stateless and usable until expiry after refresh revocation or
logout; there is no access-token deny-list.

Patient, doctor, and administrator roles are enforced by DRF permissions,
queryset scoping, and appointment service rules. Patients can read only their
appointments and cannot patch them. Doctors can update status only for their
assigned appointments. Administrators retain bounded management operations.
See [Authentication](authentication.md) and [Appointments](appointments.md).

## Abuse control

DRF anonymous, authenticated-user, and auth-endpoint scoped throttles provide
best-effort application-level rate control. The health endpoint is exempt.
These counters are not an exact distributed concurrency mechanism, brute-force
or DDoS guarantee, or WAF. The current cache topology may enforce approximately
across multiple processes. `DRF_NUM_PROXIES=0` avoids trusting forwarded client
addresses until an operator configures the exact trusted proxy count.

## Data consistency

PostgreSQL is authoritative business state. A partial unique constraint allows
cancelled-slot reuse while preventing two active appointments for the same
provider, date, and time. Lifecycle and completion rules are validated in the
appointment service, while transactions, row locks, and database constraints
remain the concurrency authority.

Reminder delivery is reconciled from qualifying appointments in PostgreSQL.
A database uniqueness constraint provides reminder idempotency, so retries and
overlapping scans cannot create duplicate reminder records. Redis transports
Celery messages; it is not reminder truth. See [Reminders](reminders.md).

## Runtime controls

The multi-stage application image runs Gunicorn, Celery worker, and Celery Beat
as UID/GID `10001:10001`. Build tools and Python package managers are absent
from the final runtime. Application source is not writable by the runtime user;
only explicit media and service-specific runtime paths are writable.

Production settings require a private Django secret, allowed hosts, and
database credentials. Forwarded HTTPS trust is explicit. The web entrypoint
does not run migrations. A one-shot release service runs migrations and static
collection before web, worker, and Beat start.

## Supply chain

- Direct dependencies compile into separate hash-locked runtime and development
  locks. CI checks lock freshness, `pip check`, and both advisory graphs.
- CI creates a CycloneDX runtime Python SBOM artifact.
- Third-party GitHub Actions use immutable commit SHAs with readable versions.
- Python, PostgreSQL, and Redis image tags include verified multi-platform
  manifest digests.
- Trivy `0.73.0` is installed in CI from a checksum-verified official archive.
  It fails on fixable OS-package HIGH or CRITICAL findings in the application,
  PostgreSQL, or Redis image.

Digest pinning improves reproducibility, not vulnerability status. Base image
updates require an intentional digest refresh. The pinned scanner executable
is stable, but its vulnerability database evolves; unchanged code can
correctly fail later when a new vulnerability is disclosed.

## Network and deployment boundaries

The production-oriented Compose topology binds only web to loopback and does
not publish PostgreSQL or Redis ports. A real operator owns network policy,
reverse proxy configuration, TLS certificates, HTTPS routing, secrets,
backups, host hardening, and deployment automation. Compose demonstrates a
topology; it is not evidence of a public production deployment.

## Logging and privacy

Every request receives an `X-Request-ID`. Safe caller values are correlation
metadata only, never identity or authorization. Invalid values are replaced
with a UUID4. Application completion logs contain only request ID, HTTP method,
path, status, and duration. They exclude request and response bodies, query
values, authorization headers, JWTs, cookies, passwords, email addresses, and
medical or notification contents. Gunicorn access/error logs coexist on
stdout/stderr and are operationally distinct from the application correlation
record.

## Known boundaries

The repository has no compliance certification, MFA, WAF, DDoS platform,
distributed DRF throttle backend, centralized log aggregation, tracing/APM, or
hosted production environment. Those boundaries should remain explicit in any
deployment review.
