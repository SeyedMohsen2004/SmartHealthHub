# Operations guide

`docker-compose.prod.yml` is a production-oriented reference topology, not
automatic deployment. It uses PostgreSQL, Redis, a one-shot release service,
Gunicorn web, a Celery worker, and exactly one Celery Beat scheduler.

## Rollout and health

Apply the release task before starting or replacing runtime services:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d db redis
docker compose --env-file .env.production -f docker-compose.prod.yml run --rm release
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --no-deps web worker beat
```

The release task runs `migrate --noinput` and `collectstatic --noinput` once.
Web startup never migrates. `/api/v1/health/` returns database readiness and is
explicitly unthrottled for probes. Operators should roll back application code
only after considering whether the applied migration remains compatible.

## Reminder services

Run exactly one Beat scheduler for this schedule. Worker and Beat may restart;
PostgreSQL reconciliation and the notification uniqueness constraint make
retries safe and recover missed due work. Redis transports queued work and its
reference volume preserves append-only broker data, but PostgreSQL remains the
reminder truth. Backups and restore testing for both persistent services remain
operator responsibilities.

Redis can warn on Linux hosts when `vm.overcommit_memory` is disabled. A real
Linux operator should evaluate Redis guidance and configure the host kernel as
appropriate for that environment. Compose and application containers do not
change host sysctls, and CI runners are not a production-host model.

## Token maintenance

SimpleJWT records outstanding and blacklisted refresh tokens. Run its official
cleanup command on an operator-controlled schedule:

```bash
python manage.py flushexpiredtokens
```

The repository deliberately does not schedule this through startup, Celery
Beat, or CI because none should access a production database implicitly.

## Secrets, network, and backups

Supply private environment values outside source control. The operator owns
secret rotation, PostgreSQL and Redis credentials/network policy, encrypted
backups, restore drills, reverse proxy trust, TLS certificates, and HTTPS
enforcement. PostgreSQL and Redis are not published by production Compose; web
binds to loopback for an operator-managed proxy.

## Logs and correlation

Gunicorn, Django, Celery, and application request logs go to stdout/stderr for
the runtime platform to collect. The application returns `X-Request-ID` and
logs the same ID with method, path, status, and duration. Use that value to
correlate a reported request without searching for bodies, query values, JWTs,
or health information, which the application completion record excludes.

## Security maintenance

Follow [dependency maintenance](dependencies.md) for intentional source and
lock updates, advisory scans, and Python SBOM generation. CI also runs Trivy
`0.73.0` against application, PostgreSQL, and Redis images for fixable
HIGH/CRITICAL OS-package vulnerabilities. The executable archive is checksum
verified; the vulnerability database is intentionally current and can make an
unchanged commit fail after a new disclosure.

Container tags are paired with manifest digests. Refresh a digest only after
inspecting the official multi-platform manifest, rebuilding, scanning, and
running the complete production smoke suite. Digest pinning prevents silent
base changes; it does not replace periodic security updates.
