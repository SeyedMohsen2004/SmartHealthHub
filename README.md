# SmartHealthHub

[![CI](https://github.com/SeyedMohsen2004/SmartHealthHub/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/SeyedMohsen2004/SmartHealthHub/actions/workflows/ci.yml)

SmartHealthHub is a production-oriented Django REST backend for role-scoped
healthcare appointments and durable in-app reminders. The project emphasizes
database-enforced invariants, reproducible builds, explicit release operations,
and testable security boundaries rather than a hosted production claim.

## Engineering highlights

- PostgreSQL-enforced active provider-slot uniqueness with deterministic booking
  and reschedule race outcomes.
- Explicit appointment lifecycle, terminal-state protection, completion-time
  validation, and cancelled-slot reuse.
- JWT access/refresh authentication with refresh rotation, blacklist-backed
  revocation, single-token logout, and bounded DRF throttling.
- Redis/Celery reminder transport reconciled from authoritative PostgreSQL state
  with database-enforced idempotency.
- Multi-stage, non-root (`10001:10001`) runtime with release-before-runtime
  migration/static handling and Gunicorn as PID 1.
- Hash-locked runtime/development dependencies, clean advisory audits, runtime
  CycloneDX SBOM, immutable-SHA Actions, digest-pinned images, and Trivy gates.
- Per-request correlation IDs and privacy-bounded operational logging.

## Architecture

Clients reach Gunicorn/Django through an operator-managed reverse proxy and TLS
boundary. Django and the release service use PostgreSQL as business-state
authority. Exactly one Celery Beat scheduler sends work through Redis to a
Celery worker, which reconciles current PostgreSQL state before writing an
in-app notification. Redis carries messages; it is not reminder truth.

See the [architecture guide](docs/architecture.md) for the component diagram,
invariants, and recovery boundaries.

## Verified quality baseline

The final `v1.1.0` baseline includes 123 tests, 95.77% statement coverage,
84.26% branch coverage, and 94.44% combined branch-aware coverage. CI enforces
a 90% combined floor and also gates
formatting, lint, Django deploy checks, migration drift, warning-free OpenAPI,
dependency freshness/audits, Docker topology, real-broker reminder behavior,
non-root runtime properties, and container vulnerabilities.

## Domain capabilities

- Patient, doctor, and administrator accounts with scoped profiles and JWT auth.
- Searchable/filterable provider directory.
- Role-scoped appointment CRUD with lifecycle and concurrency guarantees.
- User-scoped notifications plus durable appointment reminders.
- Paginated, versioned REST endpoints with generated OpenAPI and Swagger UI.

Core auth endpoints include:

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/auth/register/` | Register and issue access/refresh tokens |
| `POST` | `/api/v1/auth/login/` | Authenticate and issue access/refresh tokens |
| `POST` | `/api/v1/auth/refresh/` | Rotate refresh token and issue new access |
| `POST` | `/api/v1/auth/logout/` | Revoke one supplied refresh token |
| `GET/PATCH` | `/api/v1/auth/profile/` | Read or update the authenticated profile |

Provider, appointment, and notification CRUD remains under `/api/v1/`. The
release version is `1.1.0`; the stable API URL namespace remains `/api/v1/`.

## Security and reliability

Production settings fail fast for secrets, hosts, and database credentials.
Forwarded HTTPS/IP trust is explicit. Refresh tokens rotate; access tokens stay
short-lived and stateless. DRF throttling is best-effort application abuse
control, not exact distributed rate limiting or DDoS protection. Request logs
exclude bodies, query values, credentials, tokens, and medical content.

See [security architecture](docs/security.md) and [the reporting policy](SECURITY.md).
This repository makes no healthcare compliance certification.

## Technology

Python 3.12, Django 5, Django REST Framework, PostgreSQL, Redis, Celery,
SimpleJWT, drf-spectacular, django-filter, Gunicorn, WhiteNoise, Docker Compose,
pytest, Black, Flake8, pip-tools, pip-audit, Trivy, and GitHub Actions.

## Quick start

```bash
git clone https://github.com/SeyedMohsen2004/SmartHealthHub.git
cd SmartHealthHub
cp .env.example .env
docker compose up --build
```

Development Compose bind-mounts source and uses Django `runserver`. A one-shot
`migrate` service runs after PostgreSQL is healthy; API, worker, and Beat then
start. Local PostgreSQL and Redis ports are exposed for development convenience.

Swagger UI: <http://localhost:8000/api/docs/>

OpenAPI: <http://localhost:8000/api/schema/>

Health/readiness: <http://localhost:8000/api/v1/health/>

## Production-oriented topology

Create a private environment file from `.env.production.example`, then:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml build release
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --wait
```

The topology contains PostgreSQL, Redis, one release task, Gunicorn web, a
Celery worker, and exactly one Beat scheduler. PostgreSQL and Redis have named
volumes and are not published; web binds to loopback. The operator remains
responsible for secrets, backups, networking, reverse proxy/TLS, host tuning,
and deployment. No automatic production deployment is included.

See [operations](docs/operations.md) for migration-first rollout, restarts,
token cleanup, Redis host guidance, logs, and supply-chain maintenance.

## Testing and quality commands

Install the deterministic development environment:

```bash
python -m pip install --require-hashes -r requirements-dev.txt
python -m pip check
```

Run the principal gates:

```bash
black --check .
flake8 .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py spectacular --file schema.yml --validate --fail-on-warn
pytest --cov=accounts --cov=appointments --cov=config --cov=notifications \
  --cov=providers --cov-branch --cov-report=term-missing --cov-fail-under=90
```

The CI workflow additionally regenerates locks, audits runtime/development
graphs, creates the runtime Python SBOM, validates both Compose files, scans
production images, and exercises the disposable production-like stack.

## Documentation

- [Architecture](docs/architecture.md)
- [Security architecture](docs/security.md)
- [Operations](docs/operations.md)
- [Appointments](docs/appointments.md)
- [Authentication and throttling](docs/authentication.md)
- [Durable reminders](docs/reminders.md)
- [Dependency maintenance](docs/dependencies.md)
- [Security reporting](SECURITY.md)
- [Changelog](CHANGELOG.md)

## Release and boundaries

The current release line is `v1.1.0`; release assets include the validated
OpenAPI schema and runtime Python CycloneDX SBOM. The preserved `v1.0.0` release
documents the initial baseline.

SmartHealthHub demonstrates a production-oriented architecture and disposable
production-like CI smoke tests. It does not bundle a public deployment,
centralized observability platform, WAF/DDoS service, MFA, or compliance
certification. Email, SMS, and push delivery are intentionally absent.
