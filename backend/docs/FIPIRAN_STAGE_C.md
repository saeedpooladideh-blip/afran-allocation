# Fipiran Stage C data contract

Date: 2026-08-07

## Discovery result

The fund catalogue page is `/mf/list`. Its JavaScript-backed data contract is served
under `/services`. The adapter uses direct JSON requests first and a Playwright browser
session only when the direct method fails.

| Data | Method | Route | Response contract used |
|---|---|---|---|
| Fund types | GET | `/services/fund/fundtype` | envelope with `items[]` |
| Fund catalogue | POST | `/services/fund/fundcompare/` | `{regNos: [], showMarketMakers: false}` and `items[]` |
| Fund detail | GET | `/services/fund/getfund?regno={regNo}` | envelope with `item` |
| NAV history | GET | `/services/chart/getfundchart?regno={regNo}&showAll={bool}` | dated array |
| Net asset history | GET | `/services/chart/getfundnetassetchart?regno={regNo}&showAll={bool}` | dated array |
| Portfolio history | GET | `/services/chart/portfoliochart?regno={regNo}` | dated array |

Catalogue/detail composition fields are `stock`, `fundUnit`, `bond`, `cash`,
`deposit`, `other` and `commodity`. `fundUnit` is the only source field mapped to
`equity_fund_percentage`. The portfolio-history contract exposes `stock`, `bond`,
`cash`, `deposit`, `other` and `fiveBest`; it does not establish a historical
`fundUnit` field. The parser therefore leaves unavailable historical equity-fund and
total-equity exposure values null.

## Storage rules

- Percentages are percentage points, not fractions.
- `equity_exposure = stock_percentage + equity_fund_percentage` only when both values
  are present.
- Missing is stored as `NULL`; never as zero.
- `(fund_id, report_date)` is unique and existing observations are never overwritten.
- The calculated total is materialized with the source observation so historical
  values do not change after a parser/model release.

## Runtime verification status

The current Work cloud browser reached `https://www.fipiran.com/mf/list` but received
`502 Bad Gateway` with `Connection refused`. No Arvan runtime URL, shell, token or
console session was available in this workspace, so this is not an Arvan preflight.

Run `python scripts/stage_c_runtime_proof.py` inside the already deployed Afran
container. A passing JSON result is required before Stage C can be marked production
ready; the script has no fixture or fallback path.
