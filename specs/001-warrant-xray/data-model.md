# Data Model: Warrant X-Ray

Derived from the spec's Key Entities, [requirements.md](../../requirements.md) Section 9 and [tech_spec.md](../../tech_spec.md) Section 7. Percent fields are fractions; stored times are UTC ISO 8601; any metric may be `null` (unknown) with a reason code. Field names for source rows are inferred and unverified (T6).

## Persistent entities (SQLite)

### Snapshot
| Field | Type | Notes |
|---|---|---|
| id | int PK | Append-only, immutable |
| fetched_at | datetime UTC | |
| source_last_update | datetime \| null | Source's own time |
| row_count | int | |
| ok | bool | Failed fetches recorded but never become current |
| note | text | |
| quality_json | json | null rates, crossed quotes, duplicates, row-count change, `suspect` flag, ratio-check share |

Rule: a drop of more than 30% in rows versus the previous good snapshot marks it `suspect`; the previous good snapshot stays current (FR-DATA-06).

### WarrantRow (`warrant_rows`, PK `(snapshot_id, code)`)
Fields: code, issuer, type (`call`|`put`), underlying_ticker, expiry_date, strike, ratio_raw, underlying_bid, bid, ask, bid_volume, ask_volume, traded_volume, last_price?, last_time?, issuer_iv, issuer_eg, issuer_delta, issuer_premium, issuer_theta_raw, sensitivity_ticks, moneyness, indicators (six booleans), `valid`, `raw_json`.

Validation: non-positive strike or underlying price makes `valid=false` (excluded from lists, noted in Data health, FR-ERR-11); duplicate codes keep the first and log a data-quality note (FR-ERR-10); crossed quote (bid > ask) marks the quote invalid (FR-ERR-07); invalid or non-numeric values become `null`. `raw_json` is never exposed by the API (FR-DATA-12) and the DB file is git-ignored.

### Underlying
ticker (PK), code, name, updated_at. Refreshed with each good snapshot (FR-DATA-09).

### PriceHistory
`(ticker, day)` PK, close, source (`yahoo`|`snapshot`). Realized volatility needs at least 11 and 31 closes for 10- and 30-day windows, else `unknown`.

### Evidence
id (e.g. `E3`), turn_id, kind (`snapshot`|`metrics`|`card`|`scenario`|`news`|`health`), source, as_of, payload_json. No user message text.

### LlmCall
ts, turn_id, session_hash, model, tier, purpose, in/out/reasoning tokens, latency_ms, cost_usd, status. No personal data or raw IPs (FR-CTRL-03).

### Budget
`(day, kind)` PK, used. kind in `llm_usd`, `tavily_credits`; day is the Malaysia date; atomic updates.

### UsageMetrics
`day` (PK, YYYY-MM-DD in Malaysia time), `visit_count` (int), `unique_visitor_count` (int, computed via daily-salted one-way cryptographic hash of client subnet/User-Agent; raw IP addresses are never stored), `interactive_query_count` (int, sum of chat turns, scenario simulations, and explain-move requests). Publicly exposed via `GET /api/meta` and the Data Health tab; detailed breakdown via `GET /api/admin/metrics` (FR-020, FR-023).

### NewsCache and StoredNewsSet
- `news_cache(key, created_at, payload_json)`: 30-minute reuse (FR-NEWS-11).
- `StoredNewsSet(ticker, window_days, snapshot_id?, retrieved_at, items_json)`: **persisted for replay** so news survives outages (constitution IX). Fixed `window_days = 7` strictly (FR-016). Public article metadata only.

### Report
key `(code, snapshot_id, holding_days)`, created_at, report_json. Reused for the same key (FR-DEEP-05).

## Value objects (API and in-memory)

### WarrantMetrics (any field `null`)
shares_per_warrant, days_to_expiry, mid, size_weighted_mid, spread_pct, round_trip_cost, iv per basis (`last`, `size_weighted_mid`, `mid`, `bid`, `ask`) with reason codes; headline IV defaults to `mid`, falling back to `last` if quotes are missing (or `null` with `no_quote` if neither exists); iv_basis_spread, delta_share, gamma, vega_per_point, theta_per_day, gearing, effective_gearing, premium, breakeven_price, required_move, cross_check `{iv_diff_points, eg_diff_rel, delta_diff}`.

IV reason codes: `no_quote`, `non_positive_price`, `below_intrinsic`, `above_upper_bound`, `expired`, `solver_failed`, `non_finite`.

### WarrantCard
snapshot ref, metrics, holding_days (default 5, range 1..days left), presets `{spread_cost, flat_decay, iv_crush, gearing_check, breakeven_move}`, flags `[{code, severity(warn|high), threshold, value, text}]`, not_evaluated `[{flag, reason}]`, evidence_id, as_of, mode. Expired warrants are labeled expired with no forward-looking metrics.

Flags: HIGH_DECAY, WIDE_SPREAD, LOW_LIQUIDITY, DEEP_OTM, SHORT_EXPIRY, IV_RICH, ISSUER_MISMATCH, DATA_STALE (thresholds from `config/flags.yaml`; defaults in requirements.md Section 3). A flag lacking inputs is `not_evaluated`, never "clear" (FR-FLAG-02).

### ScenarioResult
inputs `{code, move m in [-0.5,0.5], days d in [0, days_left], iv_shift dv in [-15,15] points}`, entry_price (ask), exit_price, pnl_pct, breakeven_move (null if none in range), curve `[{horizon_days, points:[{move, pnl_pct}]}]` for horizons 0, holding, min(2x holding, days left), moves -20%..+20% in 1% steps, assumptions list, evidence_id.

Invariant: m=0, d=0, dv=0 gives pnl = bid/ask - 1 (FR-SCN-02). Non-finite results become `null` with a message.

### Attribution (explain-a-move)
Ordered parts `underlying`, `time`, `volatility`, `residual` that sum to the total mid change within 1e-9; the order is stated in the output.

### NewsItem
title (<=200), url, domain, published_date|null, retrieved_at, event_type (earnings|contract|dividend|director_dealing|corporate_action|regulatory|macro|other), facts (<=3, each <=160 chars, no URLs), stated_numbers `[{label,text}]`, corroboration_count, unconfirmed (true when one domain), extraction_method (`search_snippet`|`tavily_extract`). URL comes from Tavily only.

### RiskReport
summary (<=120 words), cost_breakdown, what_must_go_right, key_risks (each tied to evidence), counterpoints (includes red-team findings), data_limits, disclaimer.

### StockSummary
price and as_of, counts of calls/puts, issuers, expiry range, median spread cost, median flat decay, flag counts, realized vol 10/30 (or `null`), five nearest-to-the-money warrants sorted by absolute distance from strike (no recommendation wording).

### ChatSession (in memory, not persisted)
hashed id, last 10 turns, state `{snapshot_id, mode, as_of, holding_days_default}`, 2-hour idle expiry (janitor deletes). Report count capped at 3 per session.

### VisitorSession (ephemeral client-side, not persisted)
UUID in `X-Session-ID` header or cookie with 24-hour TTL; used solely to deduplicate daily visit counts into `UsageMetrics`; never linked to chat messages or raw IP addresses.

### Allowlist (per turn)
All evidence `display` strings, user-typed numbers, evidence ids; used by the grounding verifier (exact match first, rounding match second).

## State transitions

- **Snapshot**: `fetched` then `ok` (current) or `failed` or `suspect` (previous good stays current).
- **Mode**: `live` (collection allowed and enabled) to `replay` (collection off, source down, or terms disallow) to `sample` (no stored snapshots; synthetic data, badge says Sample data).
- **Chat turn**: `started` then tool steps then buffered draft then verify then (regenerate once) then strip-and-note then streamed then `done` or `error`.
