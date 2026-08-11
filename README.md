# SmartHealthHub

Backend API for a healthcare appointment management platform built with Django REST Framework.

## Features

### Authentication & Accounts

- JWT Authentication (Access & Refresh Tokens)
- User Registration
- User Login
- User Profile Management
- Role-based access control
- Supported roles:
  - Admin
  - Doctor
  - Patient

### Providers Management

- List healthcare providers
- Create provider profiles
- Update provider information
- Delete providers
- Search providers
- Filter providers
- Pagination support

### Appointments Management

- Patient appointment booking
- Appointment status tracking
- Prevent double-booking
- Provider schedule management
- Search and filtering
- Pagination support

### Notifications Management

- User notifications
- Mark notifications as read
- User-specific notification access
- Admin access to all notifications
- Pagination support

### Infrastructure

- Docker & Docker Compose
- PostgreSQL
- Swagger / OpenAPI Documentation
- Automated Testing with Pytest
- GitHub Actions CI
- Environment-based Settings
- Environment-specific Django settings

---

## Tech Stack

- Python 3.12
- Django 5
- Django REST Framework
- PostgreSQL
- Docker
- Docker Compose
- SimpleJWT
- drf-spectacular
- django-filter
- pytest
- black
- flake8
- GitHub Actions

---

## Project Structure

```text
SmartHealthHub/
├── accounts/
├── appointments/
├── notifications/
├── providers/
├── tests/
├── config/
│   ├── settings/
│   ├── api_urls.py
│   ├── urls.py
│   └── views.py
├── docker/
├── .github/workflows/
├── manage.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Running With Docker

Clone the repository:

```bash
git clone https://github.com/SeyedMohsen2004/SmartHealthHub.git
cd SmartHealthHub
```

Create environment file:

```bash
cp .env.example .env
```

Build and start services:

```bash
docker compose up --build
```

The development Compose file uses a source bind mount and Django's development
server. A one-shot `migrate` service applies migrations after PostgreSQL is
healthy, then the API starts. Django serves development static files directly;
the API container itself does not run migrations or `collectstatic`.

Run a one-off migration command when needed:

```bash
docker compose run --rm migrate
```

### Production-oriented containers

`docker-compose.prod.yml` is an opt-in production-oriented topology; it does
not deploy the project to a server. Copy the blank template and supply strong,
private values:

```bash
cp .env.production.example .env.production
```

Build the shared application image, then start the stack:

```bash
docker compose --env-file .env.production \
  -f docker-compose.prod.yml build release
docker compose --env-file .env.production \
  -f docker-compose.prod.yml up --detach --wait
```

The topology contains only PostgreSQL, a one-shot `release` service, and the
Gunicorn `web` service. PostgreSQL must be healthy before `release` runs;
`release` must successfully run migrations and collect static files before
`web` starts. Static files are collected into a named volume and mounted
read-only into `web` for WhiteNoise. Media and database data use separate
persistent volumes. Restarting only `web` does not rerun migrations.

The multi-stage Python 3.12 image keeps compilers in the builder stage and runs
as the dedicated `appuser` account (`10001:10001` by default). Gunicorn is PID
1, logs to stdout/stderr, and uses conservative environment-driven defaults.
Worker sizing remains deployment-dependent.

The web port is bound to `127.0.0.1` by default. A production operator remains
responsible for a trusted reverse proxy, public routing, TLS certificates, and
HTTPS enforcement. The image health check uses `/api/v1/health/`, including its
existing PostgreSQL readiness query. When HTTPS is terminated upstream, enable
forwarded-protocol trust only if that proxy overwrites `X-Forwarded-Proto`.
Set both forwarded-protocol trust and Django's HTTPS redirect behavior
explicitly. The checked-in blank template assumes a trusted TLS-terminating
proxy; use `False` for both only when HTTPS enforcement is handled entirely
outside Django.

The application image never runs migrations or destructive database operations
from its entrypoint. To run the release task explicitly during a later rollout:

```bash
docker compose --env-file .env.production \
  -f docker-compose.prod.yml run --rm release
docker compose --env-file .env.production \
  -f docker-compose.prod.yml up --detach web
```

### Production environment validation

`config.settings.production` fails fast unless these values are supplied:

- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`

Set `DJANGO_TRUST_X_FORWARDED_PROTO=True` only when Django is behind a trusted
proxy that overwrites the `X-Forwarded-Proto` header. Keep it false otherwise.
Neither Compose definition performs an automatic production deployment or
creates demo data.

---

## API Documentation

Swagger UI:

```text
http://localhost:8000/api/docs/
```

OpenAPI Schema:

```text
http://localhost:8000/api/schema/
```

Health Check:

```text
http://localhost:8000/api/v1/health/
```

---

## API Endpoints

### Accounts

| Method | Endpoint |
|----------|----------|
| POST | `/api/v1/auth/register/` |
| POST | `/api/v1/auth/login/` |
| POST | `/api/v1/auth/refresh/` |
| GET | `/api/v1/auth/profile/` |
| PATCH | `/api/v1/auth/profile/` |

### Providers

| Method | Endpoint |
|----------|----------|
| GET | `/api/v1/providers/` |
| POST | `/api/v1/providers/` |
| GET | `/api/v1/providers/{id}/` |
| PATCH | `/api/v1/providers/{id}/` |
| DELETE | `/api/v1/providers/{id}/` |

### Appointments

| Method | Endpoint |
|----------|----------|
| GET | `/api/v1/appointments/` |
| POST | `/api/v1/appointments/` |
| GET | `/api/v1/appointments/{id}/` |
| PATCH | `/api/v1/appointments/{id}/` |
| DELETE | `/api/v1/appointments/{id}/` |

### Notifications

| Method | Endpoint |
|----------|----------|
| GET | `/api/v1/notifications/` |
| GET | `/api/v1/notifications/{id}/` |
| PATCH | `/api/v1/notifications/{id}/` |

---

## Running Tests

Run all tests in the API container with the isolated test settings:

```bash
docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test api pytest
```

Run the same branch-aware coverage measurement enforced by CI:

```bash
docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test api pytest \
  --cov=accounts --cov=appointments --cov=config --cov=notifications \
  --cov=providers --cov-branch --cov-report=term-missing --cov-fail-under=90
```

Current baseline:

```text
48 tests passing
94.84% statement coverage
82.43% branch coverage
93.44% combined coverage
```

---

## Code Quality

Format check:

```bash
black --check .
```

Lint:

```bash
flake8 .
```

Run tests:

```bash
pytest
```

---

## CI/CD

GitHub Actions automatically runs:

- Black
- Flake8
- Django system and deployment checks
- Migration drift detection
- OpenAPI validation with warnings treated as failures
- Pytest with statement and branch coverage (90% combined floor)
- Dependency consistency checks
- Docker Compose configuration validation
- Production image build and disposable runtime smoke test

On:

- Push to `develop`
- Push to `main`
- Pull Requests

---

## Current Project Status

Implemented:

- Authentication Module
- Providers Module
- Appointments Module
- Notifications Module
- Swagger Documentation
- Pagination
- Filtering & Search
- Automated Testing
- Docker Environment
- GitHub Actions CI

Future Improvements:

- Email Notifications
- Appointment Reminder Scheduler
- Audit Logs
- Redis Caching
- Background Tasks (Celery)
- Monitoring & Observability
