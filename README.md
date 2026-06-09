# SmartHealthHub

Production-ready Django backend foundation for SmartHealthHub.

## Stack

- Python 3.12
- Django 5+
- Django REST Framework
- PostgreSQL
- Docker and Docker Compose
- JWT authentication with SimpleJWT
- OpenAPI/Swagger with drf-spectacular
- django-filter
- python-decouple
- Pytest, Black, Flake8
- GitHub Actions CI

## Project Structure

```text
SmartHealthHub/
├── accounts/
├── appointments/
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   ├── production.py
│   │   └── test.py
│   ├── api_urls.py
│   ├── urls.py
│   └── views.py
├── notifications/
├── providers/
├── tests/
├── docker/
├── .github/workflows/
├── Dockerfile
├── docker-compose.yml
├── manage.py
└── requirements.txt
```

## Quick Start

Create your environment file:

```bash
cp .env.example .env
```

Run the stack:

```bash
docker compose up --build
```

The API will be available at:

- API base: `http://localhost:8000/api/v1/`
- Health check: `http://localhost:8000/api/v1/health/`
- Swagger UI: `http://localhost:8000/api/docs/`
- OpenAPI schema: `http://localhost:8000/api/schema/`
- JWT token: `http://localhost:8000/api/v1/auth/token/`
- JWT refresh: `http://localhost:8000/api/v1/auth/token/refresh/`
- JWT verify: `http://localhost:8000/api/v1/auth/token/verify/`

## Local Development Without Docker

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set environment variables from `.env.example`, then run:

```bash
python manage.py migrate
python manage.py runserver
```

## Quality Checks

```bash
black --check .
flake8 .
pytest
```

## Configuration

Runtime settings are read from environment variables through `python-decouple`.
Use `.env.example` as the contract for required local and container settings.

Production runs through `config.settings.production`, enables secure cookies,
HSTS, SSL redirects, WhiteNoise static files, structured console logging, and
PostgreSQL persistent connections.

## API Versioning

All business APIs are mounted under `/api/v1/`. The scaffold includes app URL
modules for `accounts`, `providers`, `appointments`, and `notifications` without
domain business logic yet.
