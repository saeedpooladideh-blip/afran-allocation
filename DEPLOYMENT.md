# Stage A — Production Deployment Package

This document defines the immutable runtime contract for Afran Allocation. It does
not create, update or restart any Arvan resource.

## Release contract

| Item | Value |
|---|---|
| Runtime | Python 3.12 |
| Process manager | Gunicorn + Uvicorn Worker |
| Container port | `80/TCP` |
| Bind address | `0.0.0.0:80` |
| Health endpoint | `GET /health` |
| Persistent storage | `/data` |
| Default database | `sqlite:////data/afran.db` |
| Startup command | `sh scripts/start.sh` |
| Migration command | `python -m alembic -c alembic.ini upgrade head` |
| API compatibility | root paths and `/api/v1/...` |

## Startup guarantees

- The database volume is never cleared by application startup.
- Alembic upgrades the existing database before accepting traffic.
- A failed migration prevents the application from starting.
- The scheduler is rejected when `WEB_CONCURRENCY` is greater than one, preventing
  duplicate crawls inside a single container.
- Gunicorn receives termination signals directly because `start.sh` uses `exec`.
- The non-root `afran` user can bind port 80 through the minimal
  `CAP_NET_BIND_SERVICE` capability applied to the Python interpreter at image build.
- No credential is embedded in the image.

## Required production variables

Use the values and descriptions in `.env.example`. At minimum, explicitly set:

```text
DATABASE_URL=sqlite:////data/afran.db
DATABASE_AUTO_CREATE=false
ENVIRONMENT=production
FIPIRAN_URL=https://www.fipiran.com
SCHEDULER_ENABLED=true
WEB_CONCURRENCY=1
CRAWL_API_KEY=<project-specific-secret>
```

`CRAWL_API_KEY` must be created specifically for Afran Allocation and must not be
copied from another application.

## Build contract

```bash
docker build --pull -t afran-allocation-api:1.0.0 .
```

The image contains Chromium for the allowed Playwright failover, but HTTP/XHR remains
the primary extraction method.

## Validation contract

```bash
python -m pytest
sh scripts/release_check.sh
docker inspect --format='{{json .Config.Healthcheck}}' afran-allocation-api:1.0.0
```

The release check validates source compilation, lint, unit/integration tests, a fresh
Alembic migration, Gunicorn startup, SQLite creation and the live HTTP health response.
When Docker Engine is present, it also builds the production image.

## Stage boundary

Stage A ends with the deployable package. Dashboard implementation, live Fipiran
verification from the Arvan runtime, image push and production rollout belong to
Stages B, C and D respectively.
