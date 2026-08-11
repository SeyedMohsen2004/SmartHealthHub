#!/bin/sh
set -e

if [ -n "$POSTGRES_HOST" ]; then
  postgres_port="${POSTGRES_PORT:-5432}"
  echo "Waiting for PostgreSQL at $POSTGRES_HOST:$postgres_port..."
  while ! nc -z "$POSTGRES_HOST" "$postgres_port"; do
    sleep 1
  done
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
