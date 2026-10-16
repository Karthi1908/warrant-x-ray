# Contract: REST API

Source: [requirements.md](../../../requirements.md) Section 9 and [tech_spec.md](../../../tech_spec.md) Section 9. FastAPI generates the machine-readable OpenAPI document (FR-API-04); CI fails if generated web types drift. This file is the human-readable contract.

## Conventions

- Times are ISO 8601 UTC; percent fields are fractions; unknown values are `null` (never zero, FR-API-01).
- Every data response carries `as_of` and `mode` (`live` | `replay` | `sample`). Every data endpoint accepts optional `snapshot_id` (unknown id falls back to latest with a notice, FR-ERR-21).
- Raw source rows are never returned (FR-API-02).
- Errors: `{"error": {"code", "message", "field"?, "retry_after"?}}`. Codes: `invalid_input`, `not_found`, `rate_limited`, `budget_exhausted`, `source_unavailable`, `model_unavailable`. No stack traces; unknown `/api/*` paths return JSON 404.
- Snapshot GETs carry an `ETag` from `(snapshot_id, params)`.

## Endpoints

| Method and path | Purpose | Inputs | Notes |
|---|---|---|---|
| GET `/api/health` | Liveness | none | Used by container health check |
| GET `/api/meta` | Mode, as-of, staleness, last collection status, resolved model IDs, tier health, version, usage metrics | none | Returns public usage counts: `visits`, `unique_visitors_daily`, `interactive_queries` (FR-020) |
| GET `/api/underlyings` | Malaysian underlyings with warrant counts | snapshot_id | |
| GET `/api/warrants` | Search (FR-SRCH) | underlying, type, issuer, min_days, max_days, moneyness, sort_by, order, limit (default 10, max 20), iv_basis | `iv_basis` selects headline IV (defaults to `mid`, falling back to `last` if quotes are missing); all bases always returned. Empty stock returns an empty list with a message, not an error |
| GET `/api/warrants/{code}` | Warrant card (FR-CARD) | holding_days, snapshot_id, iv_basis? | Code case-insensitive and trimmed; headline IV defaults to `mid` (falls back to `last` if quotes are missing); unknown code returns 404 with up to 3 closest codes |
| POST `/api/scenario` | Scenario (FR-SCN) | code, underlying_move_pct, days_held, iv_shift_pts | Same function as the chat tool; out-of-range inputs rejected naming the range |
| POST `/api/compare` | Compare (FR-CMP) | codes (2 to 3), holding_days | Mixed underlyings or wrong count return a message explaining the limit; uses one snapshot |
| GET `/api/stock/{ticker}` | Stock summary (FR-STK) | holding_days | Summary plus paged warrant list (`limit`, `cursor`) |
| GET `/api/news` | News (FR-NEWS) | ticker or query, max_results (max 6) | Fixed 7-day recency window strictly (FR-016); Tavily-backed; unavailable returns `news_unavailable` result, not a 5xx |
| POST `/api/explain-move` | Decomposition (FR-EXP) | code, from_snapshot_id, to_snapshot_id | Missing inputs listed, no decomposition |
| GET `/api/snapshots` | List stored snapshots | none | |
| POST `/api/chat` | Streamed chat turn | session_id, message (1 to 1000 chars), mode (`chat`\|`deep`), snapshot_id | See [chat-sse.md](chat-sse.md) |
| GET `/api/report/{id}` | Stored Deep Risk Report | none | |
| GET `/api/sources` | Evidence records for a turn | turn_id | |
| GET `/api/admin/metrics` | Operator usage, cost, and query metrics | none (Bearer auth) | Requires `WX_ADMIN_TOKEN`; returns daily breakdowns of visits, daily uniques, query types, and token spend (FR-020, FR-023) |

Admin routes (usage and cost totals, cache clear) exist only when `WX_ADMIN_TOKEN` is set and require it as a bearer token. Anonymous visits are counted via an ephemeral `X-Session-ID` client UUID header/cookie (24h expiry); daily unique visitors use a daily-salted one-way cryptographic hash of client subnet/User-Agent (raw IP addresses are never stored).

## Limits and guards

- Chat: 30 requests per hour per hashed client key (configurable); data endpoints have a higher limit.
- Message over 1,000 characters, empty or non-text: rejected before any model call (FR-ERR-19).
- Daily LLM spend cap and Tavily credit cap: when reached, model-backed requests return stored or templated answers with a notice (FR-CTRL-02).
- Deep reports: 3 per session (configurable).

## Response entities

`WarrantCard`, `WarrantMetrics`, `ScenarioResult`, `StockSummary`, `NewsItem`, `Evidence`, `RiskReport`, `Attribution` are specified in [data-model.md](../data-model.md). Every number in these entities has a raw value and a server-formatted `display` string.

## Contract tests

One test per route validates responses against the generated OpenAPI schema using synthetic fixtures, including empty-stock, not-found, expired warrant, no-bid and stale-snapshot cases.
