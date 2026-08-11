#!/bin/sh
set -eu

# Keep PID 1 as the configured process so Unix signals reach Gunicorn directly.
# Database migrations and static collection are explicit release responsibilities.
exec "$@"
