# Afran Allocation Dashboard — Stage B

Production React + TypeScript + Tailwind frontend for the existing Afran Allocation
FastAPI. This repository does not contain or modify Backend, database, crawler or
allocation-engine code.

## Routes

- `/` — fund count, latest crawl, Fipiran state, update time and NAV summary
- `/funds` — search, fund-type filter, sortable table and server pagination
- `/allocation` — Bm 2.99%, selected-fund matching, Exposure calculation and ranking
- `/status` — Backend, database, crawler and Fipiran operational state

The application never calls Fipiran from the browser. Its same-origin read-only proxy
allows only `health`, `status` and `funds` Backend routes. Missing API values remain
missing and no demo records are generated.

## Environment

```bash
cp .env.example .env
```

Set the real Backend URL:

```text
VITE_API_URL=https://REAL-BACKEND-URL
VITE_BENCHMARK_BM=2.99
```

`VITE_API_URL` is read by the frontend server at runtime, so the same image can move
between environments without rebuilding.

## Local development

```bash
npm ci
npm run dev
```

## Production build

```bash
npm ci
npm run lint
npm test
npm run build
```

## Docker

```bash
docker build --pull -t afran-allocation-frontend:1.0.0 .
docker run --name afran-allocation-frontend \
  -p 8080:80 \
  -e VITE_API_URL='https://REAL-BACKEND-URL' \
  -e VITE_BENCHMARK_BM='2.99' \
  afran-allocation-frontend:1.0.0
```

Health check for the frontend shell:

```bash
curl --fail http://127.0.0.1:8080/
```

Backend connectivity is visible on `/status`. A healthy frontend does not claim that
Fipiran is connected unless the Backend `/status` response contains a successful run.

## Arvan image flow

```bash
export AFRAN_FRONTEND_IMAGE='YOUR_REGISTRY/afran-allocation-frontend:1.0.0'
docker build --pull -t "$AFRAN_FRONTEND_IMAGE" .
docker push "$AFRAN_FRONTEND_IMAGE"
```

At deployment, configure container port `80`, root health path `/`, and the two
variables from `.env.example`. Stage B does not create or update an Arvan resource.

## Allocation data contract

For every selected fund, the page accepts either:

- `stock_percentage` plus `equity_fund_percentage`; or
- a published `equity_exposure`.

It calculates `Exposure = Stock + Equity Fund` when both inputs exist. The completed
Backend currently does not expose these fields in its documented Fund schema, so the
page deliberately renders a dependency notice instead of fabricated rankings. Adding
that API data belongs to a later authorized Backend stage, not Stage B.
