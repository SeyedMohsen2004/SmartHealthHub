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
- Production-ready Django Configuration

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

Run migrations:

```bash
docker compose exec api python manage.py migrate
```

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

Run all tests:

```bash
docker compose exec api pytest
```

Current status:

```text
38 tests passing
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
- Django Deploy Checks
- Pytest

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