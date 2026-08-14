# Afran Allocation

Production-ready MVP for collecting Iranian investment-fund data from Fipiran,
preserving NAV history in SQLite, and exposing it through FastAPI. The container is
independent and listens on port `80`, suitable for Arvan Cloud Container.

## What is implemented

- HTML-first connectivity probe of `https://www.fipiran.com/mf/list`
- Primary extraction from Fipiran's internal JSON/XHR services
- Automatic fallback to a real Chromium session through Playwright
- Configurable timeout, exponential retry, request pacing and bounded concurrency
- Canonical parser with Persian-number and multiple response-envelope support
- Funds, NAV, performance, management and portfolio-composition data with crawl logs
- Append-only NAV/performance/exposure history; no fake values and no missing-to-zero coercion
- SQLite today with a SQLAlchemy boundary ready for PostgreSQL
- Periodic scheduler and protected manual crawl endpoint
- JSON logs, Docker health check, non-root container user and persistent volume
- Alembic migration before every production startup; application start stops on migration failure
- Stable MVP endpoints plus hidden, versioned `/api/v1/...` aliases

## Fipiran analysis captured in the adapter

Fipiran currently exposes the fund catalogue through JavaScript-backed service calls.
The adapter keeps every path configurable and currently uses:

| Purpose | Method | Configurable path |
|---|---:|---|
| Fund list | POST | `/services/fund/fundcompare/` |
| Fund types | GET | `/services/fund/fundtype` |
| Fund detail/management | GET | `/services/fund/getfund?regno=...` |
| NAV history | GET | `/services/chart/getfundchart?regno=...&showAll=...` |
| Net asset/unit flow | GET | `/services/chart/getfundnetassetchart?regno=...&showAll=...` |
| Portfolio allocation history | GET | `/services/chart/portfoliochart?regno=...` |

The list payload supplies `regNo`, name, fund type, issue/cancel/statistical NAV,
net assets, invested units, date, and daily through annual return fields. The detail
payload supplies website, registration data, manager, executive/investment manager,
auditor, custodian, guarantor and market maker when published. The chart responses
provide dated NAV, net asset, subscription and redemption observations.

Current fund list/detail payloads publish portfolio percentages as `stock`, `bond`,
`cash`, `deposit`, `other`, `commodity` and `fundUnit`. The adapter maps only the
explicit `fundUnit` field to equity-fund percentage, then freezes
`equity_exposure = stock + fundUnit` in the database. The portfolio chart currently
documents stock/bond/cash/deposit/other history but not `fundUnit`; those historical
equity-fund and total-exposure values remain `NULL` rather than being guessed as zero.

These are internal site routes rather than a documented public API. The Runtime probe
is therefore part of operations, field aliases are isolated in `DataParser`, and the
Playwright path reuses a browser session if direct HTTP is rejected.

## File layout

```text
afran/
├── app/
│   ├── api/                  # routes, dependencies, response schemas
│   ├── crawlers/             # BaseCrawler, FipiranCrawler, DataParser
│   ├── database/             # SQLAlchemy engine/session boundary
│   ├── models/               # Fund, NAV, Exposure, Performance, Manager, CrawlLog
│   ├── services/             # crawl orchestration, reads, scheduler
│   ├── utils/                # JSON logging and rate limiting
│   ├── config.py
│   └── main.py
├── scripts/probe_fipiran.py  # one-record live Runtime proof
├── scripts/start.sh          # migrate, validate workers, start Gunicorn on port 80
├── scripts/release_check.sh  # lint, tests, migration and HTTP smoke test
├── migrations/               # versioned SQLite/PostgreSQL schema
├── alembic.ini
├── tests/                    # parser, crawler, API, history and DB tests
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── requirements-dev.txt
```

## API

| Method | Path | Behavior |
|---|---|---|
| GET | `/` | Service index and health links |
| GET | `/health` | Container/DB health check |
| GET | `/funds` | Paginated list; supports `q` and `fund_type` |
| GET | `/funds/{id}` | Fund, latest NAV/performance and managers |
| GET | `/funds/{id}/history` | Paginated append-only NAV history |
| GET | `/api/v1/funds/{id}/exposure` | Latest immutable portfolio observation |
| GET | `/api/v1/exposure/ranking` | Latest complete exposures ranked descending; Bm included |
| POST | `/crawl` | Queue crawl; optional `?wait=true` |
| GET | `/status` | DB counts, crawler state and latest run/error |
| GET | `/docs` | OpenAPI UI |

Production startup requires `CRAWL_API_KEY`, and `POST /crawl` requires the same
value in `X-API-Key`. A second crawl while one is active receives HTTP `409`.

## Local execution

Python 3.12 is required.

```bash
cd afran
cp .env.example .env
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
python -m playwright install chromium
mkdir -p data
python -m alembic -c alembic.ini upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open `http://127.0.0.1:8000/docs` and verify:

```bash
curl --fail http://127.0.0.1:8000/health
curl -X POST 'http://127.0.0.1:8000/crawl?wait=true' \
  -H "X-API-Key: ${CRAWL_API_KEY}"
curl http://127.0.0.1:8000/funds
```

Run all tests:

```bash
python -m pytest
```

Run the complete Stage A release check:

```bash
sh scripts/release_check.sh
```

## Docker execution

```bash
docker compose up --build -d
docker compose ps
curl --fail http://127.0.0.1:8080/health
```

The Compose project uses only `afran-allocation-*` container, image, volume and
network names. It does not read or mount resources from another project. Container
startup applies `alembic upgrade head` and then starts Gunicorn on `0.0.0.0:80`.

## Arvan Cloud Container deployment

Build and push an immutable image to the registry connected to the Arvan account:

```bash
export AFRAN_IMAGE='YOUR_REGISTRY/afran-allocation-api:1.0.0'
docker build --pull -t "$AFRAN_IMAGE" .
docker push "$AFRAN_IMAGE"
```

Create the Arvan application from that image with container port `80`, mount a new
persistent volume at `/data`, copy only the variables from `.env.example`, set a new
project-specific `CRAWL_API_KEY`, and set health path `/health`. Do not set a custom
start command; the image already starts Gunicorn on `0.0.0.0:80`.

After deployment, run inside the new container:

```bash
python scripts/probe_fipiran.py
```

This command performs the HTML/HTTPS probe and prints one fund returned by the live
source. It never substitutes a fixture or sample record.

After the API is running inside the target container, execute the strict Stage C proof:

```bash
python scripts/stage_c_runtime_proof.py
```

It fails unless DNS, Fipiran HTTPS, a real crawl, persistence, the per-fund exposure
API and the ranking API all succeed. Its JSON output is the deployment evidence to
archive; do not replace it with unit-test fixture output.

## Operational risks and responses

1. **Internal endpoint/schema change:** paths are environment variables and all field
   aliases live in `DataParser`; failed/empty responses create failed crawl logs.
2. **WAF, cookie or JavaScript requirement:** HTTP retries first, then Playwright opens
   the list page and repeats requests inside the browser session.
3. **Partial publication:** per-fund failures produce a `partial` run; available values
   are stored and missing fields remain `NULL`.
4. **Rate limiting:** `CRAWL_MAX_RPS` and `CRAWL_DETAIL_CONCURRENCY` cap load; `429` and
   transient failures use exponential retries.
5. **Jalali/source dates:** recognizable Gregorian dates are normalized; Jalali dates
   are preserved without unsafe conversion.
6. **SQLite scale and scheduler duplication:** use one worker in this release. Move to
   PostgreSQL and a dedicated worker before horizontal scaling.
7. **Fipiran terms or robots policy:** confirm collection permission and acceptable
   frequency before production scheduling; do not bypass access controls.

See `ARCHITECTURE.md` for module boundaries and the PostgreSQL migration path.
