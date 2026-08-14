#!/bin/sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${FIPIRAN_URL:?FIPIRAN_URL is required}"
: "${ALLOCATION_BENCHMARK_BM:?ALLOCATION_BENCHMARK_BM is required}"
: "${LOG_LEVEL:?LOG_LEVEL is required}"
: "${CRAWL_INTERVAL:?CRAWL_INTERVAL is required}"
: "${CRAWL_API_KEY:?CRAWL_API_KEY is required}"
: "${WEB_CONCURRENCY:=1}"
: "${GUNICORN_TIMEOUT:=180}"
: "${GUNICORN_GRACEFUL_TIMEOUT:=30}"
: "${SCHEDULER_ENABLED:=true}"

umask 027

case "${SCHEDULER_ENABLED}" in
  true|TRUE|True|1|yes|YES|Yes|on|ON|On|y|Y|t|T)
    if [ "${WEB_CONCURRENCY}" != "1" ]; then
      echo "SCHEDULER_ENABLED requires WEB_CONCURRENCY=1 to prevent duplicate crawls." >&2
      exit 64
    fi
    ;;
esac

python - <<'PY'
import os
import tempfile
from pathlib import Path

database_url = os.environ["DATABASE_URL"]
prefix = "sqlite:///"
if database_url.startswith(prefix):
    database_path = database_url.removeprefix(prefix)
    if database_path and database_path != ":memory:":
        database_directory = Path(database_path).expanduser().resolve().parent
        database_directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=database_directory,
            prefix=".afran-write-check-",
        ):
            pass
PY

python -m alembic -c alembic.ini upgrade head

exec gunicorn app.main:app \
  --bind 0.0.0.0:80 \
  --worker-class uvicorn_worker.UvicornWorker \
  --workers "${WEB_CONCURRENCY}" \
  --timeout "${GUNICORN_TIMEOUT}" \
  --graceful-timeout "${GUNICORN_GRACEFUL_TIMEOUT}" \
  --access-logfile - \
  --error-logfile -
