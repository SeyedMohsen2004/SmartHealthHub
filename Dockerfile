FROM python:3.12-slim AS runtime-builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY requirements.txt ./requirements.txt

RUN pip install --require-hashes --requirement requirements.txt \
    && pip check


FROM runtime-builder AS development-builder

COPY requirements-dev.txt ./requirements-dev.txt
RUN pip install --require-hashes --requirement requirements-dev.txt


FROM python:3.12-slim AS application

ARG APP_UID=10001
ARG APP_GID=10001

ENV DJANGO_SETTINGS_MODULE=config.settings.production \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --gid "${APP_GID}" appgroup \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" \
        --create-home --home-dir /home/appuser --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R appuser:appgroup /app /home/appuser

WORKDIR /app

COPY manage.py gunicorn.conf.py ./
COPY accounts ./accounts
COPY appointments ./appointments
COPY config ./config
COPY notifications ./notifications
COPY providers ./providers
COPY --chmod=0755 docker/entrypoint.sh /usr/local/bin/container-entrypoint

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; request = urllib.request.Request('http://127.0.0.1:8000/api/v1/health/', headers={'X-Forwarded-Proto': 'https'}); urllib.request.urlopen(request, timeout=4).read()"]

ENTRYPOINT ["/usr/local/bin/container-entrypoint"]


FROM application AS development

COPY --from=development-builder /opt/venv /opt/venv

USER appuser:appgroup

CMD ["gunicorn", "--config", "gunicorn.conf.py", "config.wsgi:application"]


FROM application AS runtime

COPY --from=runtime-builder /opt/venv /opt/venv

# The final image needs application packages, not installers or build tooling.
RUN /opt/venv/bin/python -m pip uninstall --yes pip setuptools wheel \
    && /usr/local/bin/python -m pip uninstall --yes pip setuptools wheel

USER appuser:appgroup

CMD ["gunicorn", "--config", "gunicorn.conf.py", "config.wsgi:application"]
