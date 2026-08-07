#!/bin/sh
set -eu

: "${WEB_CONCURRENCY:=1}"
: "${GUNICORN_TIMEOUT:=180}"
: "${GUNICORN_GRACEFUL_TIMEOUT:=30}"
: "${SCHEDULER_ENABLED:=true}"

case "${SCHEDULER_ENABLED}" in
  true|TRUE|1|yes|YES)
    if [ "${WEB_CONCURRENCY}" != "1" ]; then
      echo "SCHEDULER_ENABLED requires WEB_CONCURRENCY=1 to prevent duplicate crawls." >&2
      exit 64
    fi
    ;;
esac

python -m alembic -c alembic.ini upgrade head

exec gunicorn app.main:app \
  --bind 0.0.0.0:80 \
  --worker-class uvicorn_worker.UvicornWorker \
  --workers "${WEB_CONCURRENCY}" \
  --timeout "${GUNICORN_TIMEOUT}" \
  --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT}" \
  --access-logfile - \
  --error-logfile -
