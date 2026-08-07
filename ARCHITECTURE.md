# Afran Allocation Architecture

## Boundaries

The application has four explicit boundaries:

1. **Source adapter** — `app/crawlers/` owns every Fipiran-specific URL, field alias,
   HTTP rule and Playwright fallback. `BaseCrawler` is the contract for adding a
   different source later.
2. **Canonical records** — crawler dataclasses are the stable hand-off between any
   source and the rest of the application. Source payloads never leak into API logic.
3. **Application services** — `CrawlService` validates and persists a crawl;
   `FundService` owns read queries; `CrawlScheduler` owns periodic execution.
4. **Delivery and storage** — FastAPI routes depend on services, while SQLAlchemy
   models depend only on the database boundary.

```text
Fipiran HTML
    │ probe
    ▼
HTTP/XHR adapter ──failure──► Playwright session adapter
    │                              │
    └──────── canonical records ◄──┘
                    │
                    ▼
              CrawlService
             ┌──────┴──────┐
             ▼             ▼
      SQLAlchemy/SQLite   CrawlLog
             │
             ▼
      FastAPI /api/v1 + compatibility routes
```

## Persistence rules

- `funds.external_id` stores Fipiran's `regNo` and is unique.
- Master fund metadata is refreshed on each successful observation.
- `fund_navs` is unique by `(fund_id, nav_date)` and historical observations are
  insert-only. A repeated crawl does not overwrite that date.
- `fund_performances` follows the same rule by `(fund_id, as_of_date)`.
- Manager records retain first/last seen timestamps.
- Every run starts with a durable `running` row and ends as `success`, `partial`,
  or `failed`, including counts, duration and a sanitized error.
- Missing upstream values remain `NULL`; they are never converted to zero.

## PostgreSQL migration

The repository uses portable SQLAlchemy types and Alembic migrations. Set
`DATABASE_URL` to a `postgresql+psycopg://...` URL and run
`python -m alembic upgrade head`; no crawler or API code must change. Production
sets `DATABASE_AUTO_CREATE=false`, so schema changes cannot bypass migrations.

The container startup sequence is intentionally atomic:

1. validate scheduler/worker concurrency;
2. apply all pending migrations;
3. replace the shell process with Gunicorn bound to port 80.

If a migration fails, Gunicorn never starts and the container health check remains
failed instead of exposing a partially upgraded application.

## Concurrency model

Upstream detail requests use a bounded semaphore and a process-local rate limiter.
The crawl service prevents overlapping jobs. Because the first release combines the
scheduler and SQLite in one process, the container intentionally runs one Gunicorn
worker. Scale-out should split the scheduler into a worker and use PostgreSQL plus a
distributed job lock.
