# Phase 0 Research: Warrant X-Ray

Date: 2026-10-14. Basis: [tech_spec.md](../../tech_spec.md) (vendor docs read 2026-10-13 by its author) and the spec clarification. No new vendor facts were verified in this step; anything marked **VERIFY** stays unconfirmed and maps to a task (T1 to T10) that must be run and recorded in `docs/VERIFIED.md` before dependent code is trusted.

## Status of "NEEDS CLARIFICATION"

None remain in the plan's Technical Context as blocking design. All unknowns are verification spikes with fallbacks, so planning can proceed. Decision gates:

| Gate | After | Decision |
|---|---|---|
| A | T1, T2 | Keep ADK + `LiteLlm`, switch to a custom `BaseLlm`, or fall back to a plain loop |
| B | T6 | Collect live data, or run on a curated set and replay only (spec clarification: replay-only if terms forbid collection) |
| C | T10 | Final tier mapping and timeouts |

## Decisions

### R1. Orchestration: Google ADK behind a framework-agnostic tool layer
- **Decision**: ADK `LlmAgent` (+ `SequentialAgent` for deep report, `Runner`, `App`, plugin) wrapping plain async tool functions with no ADK imports (D1).
- **Rationale**: ADK gives the tool loop, sessions, lifecycle hooks; the tool boundary keeps a cheap escape hatch.
- **Alternatives**: plain hand-written loop (kept as fallback, Gate A); LangGraph (not chosen by the user).
- **Open**: LlmAgent keyword names, `output_schema` with tools, `temp:` state, plugin reach into sub-agents, tool default params (T3).

### R2. LLM gateway: Nebius Token Factory via OpenAI-compatible API
- **Decision**: base URL `https://api.tokenfactory.nebius.com/v1/`, bearer key from `WX_NEBIUS_API_KEY`; ADK `LiteLlm` with `openai/` prefix for agents, OpenAI SDK for single-shot calls.
- **Rationale**: Documented OpenAI-compatible API; matches the constitution (Nebius + Nemotron only).
- **Alternatives**: custom `BaseLlm` over the OpenAI SDK (Gate A fallback).
- **Open**: LiteLLM handling of two-slash model IDs and Nemotron tool calls (T2).

### R3. Model tiers
- **Decision**: Nano for extraction, entity fallback and intent check; Super for chat and evidence collection; Ultra for the Deep Risk Report; optional Lightning as a faster chat tier. Candidate IDs live in config, validated against `/v1/models` at startup.
- **Rationale**: Cost/latency fit per role (FR-CTRL-04).
- **Alternatives**: all-Super or all-Ultra (the ablation eval compares them).
- **Open**: exact IDs, the Ultra 256K vs 1,024K context conflict, prices, rate limits (T4); latency (T10). IDs in the tech spec come from vendor pages and third parties, not a live call.

### R4. Reasoning models
- **Decision**: generous `max_tokens`, low reasoning effort on tool turns, strip reasoning content in an after-model hook, never log reasoning text.
- **Rationale**: A May 2026 Nebius issue reports reasoning exhausting small budgets and 400s with tools; the vendor page now lists tool calling. The conflict is settled by test.
- **Open**: T1 matrix, T9 (where reasoning appears).

### R5. News: Tavily only
- **Decision**: `AsyncTavilyClient` search (topic news, domain/time filters) then extract for up to 3 URLs; fixed 7-day recency window strictly (FR-016); Nano structures items into a strict schema; corroboration by ticker, event type, date window, title similarity or shared number; 30-minute reuse cache.
- **Rationale**: Constitution VII; raw web text never reaches Super/Ultra (injection defense); fixed 7-day window eliminates noise and prevents query parameter drift.
- **Alternatives**: crawl/research endpoints are behind off-by-default flags.
- **Open**: coverage and `published_date` for Malaysian domains, extraction on exchange announcement pages, credits per call (T5).

### R6. Verification before streaming
- **Decision**: buffer answer text, verify by exact string match against per-turn `display` allowlist (plus rounded-numeric fallback), lint advice, regenerate once, then strip sentences and add the note; then stream (D3, D4).
- **Rationale**: Constitution I and III are hard rules; exact strings beat float tolerance.
- **Trade-off**: slower perceived answers; mitigated by streaming status/evidence/cards early. `WX_STREAM_DRAFT` exists only as an off-by-default experiment.

### R7. Quant engine
- **Decision**: NumPy/SciPy pure functions; Black-Scholes European no-dividend; Brent IV solve on `[1e-4, 5.0]` with no-arbitrage bound checks and reason codes; IV on five bases (last, size-weighted mid, mid, bid, ask); ratio convention chosen by median error test on a real snapshot; sequential attribution.
- **Rationale**: Matches FR-CALC-*; golden values are in the functional spec.
- **Note**: the functional spec (FR-CALC-02, card "headline uses mid") and tech spec (headline default size-weighted mid, extra "last" basis) differ. **Reconcile in tasks**: treat the functional spec as the contract (mid headline, bid/mid/ask bases) and the tech spec bases as an additive extension, default headline `mid` until the owner decides.
- **Open**: ratio direction, exercise style, theta meaning (T6, OI-02, OI-03).

### R8. Storage and replay
- **Decision**: SQLite WAL via SQLAlchemy 2/aiosqlite; append-only snapshots; derived data cached by `(snapshot_id, code, params)`; synthetic fixture generator for CI and fallback.
- **Rationale**: Simple, reproducible, no extra service.
- **Alternatives**: object-storage file or managed DB (T7 options B, C).
- **Open**: persistence on Nebius, always-on instance (T7).

### R9. Source collection
- **Decision**: `httpx` POST to the screener endpoint, identifying User-Agent, 5 s pacing, backoff, kill-switch; collection gated on terms confirmation.
- **Rationale**: Constitution VI and spec clarification.
- **Open**: everything about the real response format and permission (T6, OI-01 to OI-05). Field names in the tech spec are inferred.

### R10. Price history for realized volatility
- **Decision**: `HistoryProvider` with Yahoo (`.KL`) and snapshot-derived implementations; otherwise volatility context is unknown and `IV_RICH` is listed as not evaluated.
- **Open**: Yahoo coverage and terms (T8, OI-07).

### R11. Replay for news (gap found in review)
- **Decision**: persist Tavily-derived `NewsItem` sets keyed by `(snapshot_id or fetch time, ticker, window)` in a `StoredNewsSet` table, in addition to the 30-minute cache; ship synthetic news fixtures marked `ILLUSTRATIVE`.
- **Rationale**: Constitution IX requires replay to work during outages, but `news_cache` only keeps 30 minutes, so weekend replay would lose news.
- **Privacy check**: stores public article metadata only, no user text.

### R12. Privacy of persisted data (gap found in review)
- **Decision**: `evidence`, `llm_calls` and turn records keep hashed session ids and no user message text; logs truncate messages to a configurable length (default 80 chars, can be off).
- **Rationale**: Constitution XI and FR-G-05.

### R13. Frontend
- **Decision**: Vite + React + TS strict, Tailwind with design tokens, Radix primitives, TanStack Query/Table/Virtual, Zustand, Recharts, `fetch-event-source`, generated API types, sanitized Markdown with `[E#]` chips.
- **Rationale**: Section 10 of the tech spec; accessibility (WCAG AA, keyboard, no color-only meaning) is required by FR-UI-07.
- **Note**: the UI never recomputes numbers; formatting mirrors server rules and is tested against shared fixtures.

### R14. Testing and CI
- **Decision**: tests before quant functions; one test per M/S requirement named with its FR id; `FakeLlm` for deterministic agent flow; contract tests from OpenAPI; Playwright + axe in replay mode with the stub model; secret scan and dependency audit in CI; merge blocked on red.
- **Rationale**: Constitution agent rules and SC-009.

### R15. Deployment
- **Decision**: one image, one always-on instance (in-memory sessions, in-process scheduler), commands recorded in `docs/DEPLOY.md` only after reading Nebius docs.
- **Open**: all Nebius-specific features (T7).

### R16. Privacy-Preserving Usage Metrics Tracking
- **Decision**: Track visits via ephemeral client session UUIDs (`X-Session-ID` header/cookie, 24h expiry) and daily unique visitors via a daily-salted one-way cryptographic hash of client subnet/User-Agent; raw IP addresses are never logged or stored. Count interactive queries across chat turns, scenario simulations, and explain-move requests. Expose aggregates via `GET /api/meta`, the public Data Health tab, and operator admin metrics (`GET /api/admin/metrics`).
- **Rationale**: Mandated by constitution Principle XI (Privacy by Design) and FR-005, FR-020, FR-023.
- **Alternatives**: Client local storage only (rejected because public/operator dashboard requires server-aggregated counts).

### R17. Language Scope & Safety Boundary
- **Decision**: Chat detects Malay language; advice and price-prediction requests in Malay are strictly declined in Malay using deterministic safety templates. Non-advice queries in Malay may fall back to English for MVP. Full Malay translation across every response type remains an optional (C) priority.
- **Rationale**: Balances regulatory safety (zero financial advice in any supported language) with MVP implementation scope (FR-017, SC-002).
- **Alternatives**: Full dual-language localization for all tools and reports in MVP (deferred to Phase C).

## Constitution re-check after Phase 1 design

All eleven principles remain PASS. The two actions found at the gate (persisted news for replay, no message text in storage) are reflected in R11, R12 and the data model.

## Spec/Requirement reconciliations to carry into `/speckit-tasks`

1. Headline IV basis: functional spec says mid, falling back to last traded price if quotes are missing (or null with reason code no_quote); tech spec adds size-weighted mid and bid/ask bases. All five bases computed and user-toggleable.
2. Functional spec lists golden values for vega as "per 1.00 of sigma" and the card shows "vega per volatility point"; keep both unit conversions explicit and tested.
3. Spec Story 7 "Explain a move" was partly trimmed in the spec file's Story 2 text; keep FR-EXP-* in scope as S priority.
4. License choice: MIT License.
5. Risk-free rate: single source of truth declared in `config/flags.yaml` under `risk_free_rate: 0.03`, with quant engine falling back to `0.03` (FR-023, OI-08).
6. Session model: distinct `ChatSession` (in-memory, 2-hour idle expiry, last 10 turns) and `VisitorSession` (ephemeral client UUID, 24-hour TTL for visit deduplication).
7. Holiday calendars: 2026 and 2027 Bursa exchange trading calendars verified from official circulars during spike T6 (T013) into static `config/bursa_holidays.yaml`; scheduler treats holidays as planned market closures.
