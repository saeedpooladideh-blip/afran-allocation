#!/bin/sh
set -eu

release_tmp="$(mktemp -d)"
server_pid=""

cleanup() {
  if [ -n "${server_pid}" ]; then
    kill "${server_pid}" 2>/dev/null || true
  fi
  rm -rf "${release_tmp}"
}
trap cleanup EXIT INT TERM

python -m compileall -q app migrations scripts tests
ruff check app migrations scripts tests
python -m pytest

DATABASE_URL="sqlite:///${release_tmp}/migration.db" \
DATABASE_AUTO_CREATE=false \
python -m alembic -c alembic.ini upgrade head

DATABASE_URL="sqlite:///${release_tmp}/runtime.db" \
DATABASE_AUTO_CREATE=false \
SCHEDULER_ENABLED=false \
python -m alembic -c alembic.ini upgrade head

DATABASE_URL="sqlite:///${release_tmp}/runtime.db" \
DATABASE_AUTO_CREATE=false \
SCHEDULER_ENABLED=false \
LOG_LEVEL=WARNING \
gunicorn app.main:app \
  --bind 127.0.0.1:18080 \
  --worker-class uvicorn_worker.UvicornWorker \
  --workers 1 \
  --timeout 30 \
  --access-logfile - \
  --error-logfile - >"${release_tmp}/gunicorn.log" 2>&1 &
server_pid=$!

attempt=0
while [ "${attempt}" -lt 20 ]; do
  if python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:18080/health', timeout=2)" \
    >/dev/null 2>&1; then
    break
  fi
  attempt=$((attempt + 1))
  sleep 0.25
done

python - <<'PY'
import json
import urllib.request

with urllib.request.urlopen("http://127.0.0.1:18080/health", timeout=3) as response:
    payload = json.load(response)
    assert response.status == 200
    assert payload["status"] == "healthy"
print("gunicorn-healthcheck-ok")
PY

if command -v docker >/dev/null 2>&1; then
  docker build --pull -t afran-allocation-api:release-check .
else
  echo "docker-engine-unavailable: image build skipped" >&2
fi
