# Tasks: Warrant X-Ray

**Input**: Design documents from `/specs/001-warrant-xray/` (spec.md, plan.md, research.md, data-model.md, contracts/, quickstart.md); detail in `requirements.md` (`FR-*`, `AC-*`) and `tech_spec.md`.
**Prerequisites**: plan.md, spec.md (done); constitution v1.1.0.

**Tests**: INCLUDED. The constitution requires tests before quant functions and CI green before merge; requirements.md asks for one test per M and S requirement named with its requirement ID. Write each test first and see it fail.

**Naming**: "spike T1..T10" refers to the verification tasks in `tech_spec.md` Section 14 (record results in `docs/VERIFIED.md`); T001... are the task ids in this file. Never treat a VERIFY item as fact until its spike is recorded. Mark every assumption in code with `# ASSUMPTION`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 to US8 map to spec.md user stories

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Create repository skeleton per plan.md (`src/warrantx/{quant,data,tools,llm,news,agents,guardrails,api,eval}`, `config/`, `scripts/`, `tests/{unit,integration,contract,fixtures}`, `web/`, `docs/`) with empty `__init__.py` files
- [X] T002 Initialize Python project in `pyproject.toml` (Python 3.11+, deps per tech_spec Section 3) and run `uv lock`; commit `uv.lock` (pin versions here, do not guess elsewhere)
- [X] T003 [P] Configure ruff, mypy (strict for `src/warrantx/quant/`), pytest markers (`live`), pre-commit in `pyproject.toml` and `.pre-commit-config.yaml`
- [X] T004 [P] Initialize web app in `web/` (Vite, React, TypeScript strict, Tailwind, Radix, TanStack Query/Table/Virtual, Zustand, Recharts, fetch-event-source, openapi-typescript/openapi-fetch, Vitest, Playwright, axe-core, ESLint, Prettier) per R13
- [X] T005 [P] Add `.gitignore` (data/, `.env`, raw captures, `web/dist`, caches), `.env.example` with all `WX_*` names and no values, and verify `LICENSE` (MIT License) in project root
- [X] T006 [P] Create GitHub Actions workflows `.github/workflows/ci.yml` with jobs `backend`, `web`, `e2e`, `security` (gitleaks, pip-audit, npm audit) per tech_spec Section 13
- [X] T007 [P] Create `docs/DECISIONS.md`, `docs/VERIFIED.md`, `docs/DEPLOY.md`, `docs/FEEDBACK.md` with headings and the VERIFY/spike tables from tech_spec Section 14
- [X] T008 [P] Write `Dockerfile` (multi-stage: build `web/dist`, install from lockfile, non-root user, health check) and `docker-compose.yml` with volume for the SQLite file

---

## Phase 2: Foundational (Blocking Prerequisites)

**CRITICAL**: No user story work until this phase is complete.

### Verification spikes (decide whether the plan holds; run first)

- [ ] T009 Run spike T1 (Nemotron capability matrix on Token Factory with the OpenAI SDK) via `scripts/spikes/t1_matrix.py`; record results in `docs/VERIFIED.md` (needs `WX_NEBIUS_API_KEY`; STOP and ask if the key is missing)
- [ ] T010 Run spike T2 (ADK `LiteLlm` loop with two tools against Token Factory) via `scripts/spikes/t2_adk_loop.py`; record in `docs/VERIFIED.md`
- [X] T011 Run spike T3 (ADK behaviors: non-streaming text with function calls, `output_schema` with/without tools, `temp:` state, plugin reach into sub-agents, tool default params, `BaseLlm` signature, `LlmAgent` kwargs) via `scripts/spikes/t3_adk_behaviors.py`; record in `docs/VERIFIED.md`
- [X] T012 Decision Gate A: from T009 to T011 choose ADK + `LiteLlm`, custom `BaseLlm`, or plain loop; write the decision to `docs/DECISIONS.md` (affects T037 to T039)
- [X] T013 [P] Run spike T6 (capture one real source response to a git-ignored folder, confirm field names/units, ratio direction, exercise style, theta/sensitivity meaning, hours, 2026 and 2027 holiday calendar verification via official Bursa circulars, terms of use) via `scripts/spikes/t6_capture.py`; record in `docs/VERIFIED.md`
- [X] T014 Decision Gate B: from T013 decide live collection vs replay-only on a curated set (spec clarification); record in `docs/DECISIONS.md` (affects US4)
- [ ] T015 [P] Run spikes T4 (`/v1/models`, IDs, limits, prices), T5 (Tavily Malaysian domain coverage and `published_date`), T9 (where reasoning content appears) via `scripts/spikes/`; record in `docs/VERIFIED.md` and fill `config/prices.yaml` and `config/sources.yaml` with dated values

### Core infrastructure

- [X] T016 Implement settings with `pydantic-settings` (prefix `WX_`, required keys by mode, startup validation) in `src/warrantx/config.py` and YAML loaders/validators for `config/*.yaml`
- [X] T017 [P] Create default config files `config/flags.yaml` (thresholds and `risk_free_rate: 0.03` fallback per FR-023), `config/linter_patterns.yaml`, `config/samples.yaml`, `config/bursa_holidays.yaml` (populated for 2026 and 2027; marked unverified until T013 verification)
- [X] T018 Define SQLAlchemy 2 async models and repository interface for snapshots, warrant rows, underlyings, price history, evidence, llm_calls, news cache, stored news sets, budgets, usage metrics (visits, daily-salted hashed uniques, queries count), reports per data-model.md in `src/warrantx/data/repo.py` (WAL, FKs on, append-only snapshot tables)
- [X] T019 [P] Define Pydantic models `WarrantSnapshot`, `WarrantMetrics`, `WarrantCard`, `ScenarioResult`, `NewsItem`, `Evidence`, `RiskReport`, `StockSummary`, `Attribution` in `src/warrantx/tools/models.py` (every number has raw value and display string; unknown is `None`)
- [X] T020 [P] Implement display formatting (single source of truth) and `Evidence.wrap` in `src/warrantx/tools/evidence.py`
- [X] T021 [P] Implement structured logging with request ids and redaction rules (no keys, raw IPs, message text beyond truncation, reasoning) in `src/warrantx/api/logging.py`
- [X] T022 [P] Implement stable error codes and error-shape handlers in `src/warrantx/api/errors.py`
- [X] T023 Implement synthetic fixture generator (several underlyings, calls/puts, varied expiries, crossed quotes, missing bids, duplicates, invalid rows) in `scripts/make_fixtures.py`; output labeled synthetic; never real data
- [X] T024 [P] Implement `FakeLlm` (`BaseLlm` subclass, scripted function calls and texts keyed by scenario) in `src/warrantx/llm/fake.py`
- [X] T025 [P] Implement guardrail templates (disclaimer, refusal, omission note, degraded messages; English and Malay) in `src/warrantx/guardrails/templates.py`
- [X] T026 Create FastAPI app skeleton with lifespan, routers `meta`, `data`, `chat`, `report`, `admin`, `/api/health`, anonymous session UUID (`X-Session-ID`) and daily-salted subnet/UA hashing middleware (raw IPs never stored), JSON 404 for `/api/*`, SPA static mount with `index.html` fallback in `src/warrantx/api/app.py`
- [X] T027 [P] Add OpenAPI export, web type generation step (`openapi-typescript`), and gzipped bundle size budget check (<300 KB gzipped, SC-010) in `web/package.json` and `.github/workflows/ci.yml`

**Checkpoint**: foundation ready; spikes recorded; gates A and B decided.

---

## Phase 3: User Story 1 - See what holding a warrant really costs (Priority: P1) MVP

**Goal**: A warrant card with issuer vs recomputed metrics, cost-of-holding items and flags, backed by the pure quant engine.
**Independent Test**: With a synthetic snapshot, request a card with a 5-day hold; verify side-by-side values, presets, flags, as-of and mode, and golden/parity/IV round-trip tests (AC-01, AC-15, AC-16, AC-20).

### Tests for User Story 1 (write FIRST, must FAIL)

- [X] T028 [P] [US1] Golden-value, put-call-parity and monotonicity tests for Black-Scholes in `tests/unit/quant/test_bs.py` (FR-CALC-04, FR-CALC-05, FR-CALC-06)
- [X] T029 [P] [US1] IV round-trip grid, bounds and reason-code tests in `tests/unit/quant/test_iv.py` (FR-CALC-02, FR-CALC-07, FR-ERR-09)
- [X] T030 [P] [US1] Metrics tests (headline IV defaulting to `mid` with `last`-quote fallback, size-weighted mid, spread, round-trip cost, gearing, effective gearing, premium, breakeven, required move, expired and no-quote cases) in `tests/unit/quant/test_metrics.py` (FR-CALC-03, FR-CARD-05)
- [X] T031 [P] [US1] Flag threshold tests including not-evaluated cases in `tests/unit/quant/test_flags.py` (FR-FLAG-01 to 03, FR-ERR-13)
- [X] T032 [P] [US1] Ratio-convention test on the fixture set in `tests/unit/quant/test_ratio.py` (FR-CALC-01)
- [X] T033 [P] [US1] Hypothesis property test (no exceptions, no NaN, finite or `None`) and performance benchmark (300 warrants with 5 IV bases under 1.0 s on 1 core, SC-010) in `tests/unit/quant/test_properties.py` (FR-CALC-03, FR-ERR-23)
- [X] T034 [P] [US1] Contract tests for `GET /api/warrants/{code}` (found, not found with 3 closest, expired, no bid) in `tests/contract/test_card.py` (FR-CARD-01 to 05)

### Implementation for User Story 1

- [X] T035 [P] [US1] Implement Black-Scholes price, Greeks (delta, gamma, vega per point, theta per day) and no-arbitrage bounds in `src/warrantx/quant/bs.py`
- [X] T036 [P] [US1] Implement Brent IV solver and `iv_by_basis` (bid, mid, ask, size-weighted mid, optional last) in `src/warrantx/quant/iv.py`
- [X] T037 [US1] Implement vectorized `compute_metrics` in `src/warrantx/quant/metrics.py` (headline IV defaulting to `mid`, falling back to `last` if quotes missing; <1.0 s budget for 300 warrants; depends on T035, T036)
- [X] T038 [P] [US1] Implement ratio convention selection in `src/warrantx/quant/ratio.py`
- [X] T039 [US1] Implement flags engine and cost-of-holding presets (spread cost, flat decay, IV crush, breakeven move) in `src/warrantx/quant/flags.py` (depends on T037)
- [X] T040 [US1] Implement card builder with issuer vs recomputed cross-check (using headline IV mid or last fallback) and difference markers in `src/warrantx/tools/warrants.py` (FR-XCHK-01, FR-XCHK-02, FR-CARD-02)
- [X] T041 [US1] Implement `GET /api/warrants/{code}` with ETag and snapshot pinning in `src/warrantx/api/routes/data.py`
- [X] T042 [P] [US1] Web: Card tab with `MetricPair`, `HoldingCostBar`, `FlagChip`, `FlagDrawer`, holding-days stepper in `web/src/features/card/`
- [X] T043 [P] [US1] Web: shared formatting and copy (no recommendation words, glossary tooltips) in `web/src/lib/format.ts`, `web/src/lib/copy.ts`, `web/src/lib/glossary.ts` with shared-fixture tests

**Checkpoint**: card works end to end offline and golden tests pass.

---

## Phase 4: User Story 2 - Grounded chat that explains, never advises (Priority: P1)

**Goal**: Streamed chat with tool calling, verify-before-stream grounding, advice boundary and injection defense.
**Independent Test**: Run sample prompts with `FakeLlm` in replay; verify numbers traceable, advice boundary in English and Malay, injection canary ignored (AC-06, AC-07, AC-08, AC-10, AC-11).

### Tests for User Story 2 (write FIRST, must FAIL)

- [X] T044 [P] [US2] Verifier tests (every number format, rounding edge, user-typed numbers, evidence ids, pass/fail corpus, strip-and-note) in `tests/unit/guardrails/test_verifier.py` (FR-GRD-01 to 03)
- [X] T045 [P] [US2] Advice linter and intent tests with English and Malay corpora (declining advice/predictions in Malay, non-advice English fallback, FR-017) in `tests/unit/guardrails/test_linter_intent.py` (FR-ADV-01 to 03)
- [X] T046 [P] [US2] Injection sanitizer and canary tests in `tests/unit/guardrails/test_injection.py` (FR-NEWS-09, FR-ERR-22)
- [X] T047 [P] [US2] Agent-flow integration tests with `FakeLlm` (tool calls, evidence, regenerate once, strip-and-note, partial on timeout, tier fallback) in `tests/integration/test_agent_flow.py` (FR-CHAT-*, FR-ERR-16, FR-ERR-17)
- [X] T048 [P] [US2] SSE protocol tests (first status event <= 3.0 s per SC-010, event order, heartbeat, cancel on disconnect, verified-before-stream) in `tests/integration/test_sse.py` per contracts/chat-sse.md
- [X] T049 [P] [US2] Name-matching tests (exact, fuzzy, ambiguity question, no match with 3 suggestions) in `tests/unit/tools/test_entity.py` (FR-NAME-01 to 04, AC-06)

### Implementation for User Story 2

- [X] T050 [P] [US2] Implement grounding verifier and `strip_and_note` in `src/warrantx/guardrails/verifier.py`
- [X] T051 [P] [US2] Implement advice linter in `src/warrantx/guardrails/linter.py` (detecting Malay and declining advice in Malay, non-advice fallback to English, FR-017) and advice-intent pre-check (rules first, Nano if ambiguous) in `src/warrantx/guardrails/intent.py`
- [X] T052 [P] [US2] Implement injection filters in `src/warrantx/guardrails/injection.py`
- [X] T053 [P] [US2] Implement model tier factories, reasoning-effort config, fallback chain and circuit breaker in `src/warrantx/llm/models.py`; startup `/v1/models` check
- [X] T054 [P] [US2] Implement direct Nano structured-call client with JSON repair retry in `src/warrantx/llm/direct.py`
- [X] T055 [P] [US2] Implement usage and cost logging in `src/warrantx/llm/usage.py` and `src/warrantx/llm/pricing.py` (no personal data)
- [X] T056 [US2] Implement entity resolution tool (exact, rapidfuzz, Nano choice among top 10, clarifying question) in `src/warrantx/tools/entity.py`
- [X] T057 [US2] Implement tool registry with status-text map and ADK wrappers (tools take identifiers and numbers only, no URLs) in `src/warrantx/tools/registry.py` and `src/warrantx/agents/app.py`
- [X] T058 [US2] Implement `GuardrailPlugin` (budget, tool arguments, call caps, evidence wrapping, reasoning stripping) in `src/warrantx/guardrails/plugin.py`
- [X] T059 [US2] Implement root agent and prompts (answer-first order, copy display strings verbatim, untrusted-data wrapper rule) in `src/warrantx/agents/root.py` and `src/warrantx/agents/prompts/`
- [X] T060 [US2] Implement turn runner (advice pre-check, ADK run, verify, regenerate once, strip, stream chunks, persist evidence, increment interactive query count per FR-020) in `src/warrantx/api/routes/chat.py` and `src/warrantx/api/sse.py`
- [X] T061 [US2] Implement rate limit (hashed client key) and budget guard in `src/warrantx/api/ratelimit.py` and `src/warrantx/api/budget.py` (FR-CTRL-01, FR-CTRL-02)
- [X] T062 [US2] Implement `ChatSession` janitor (in-memory 2-hour idle expiry, 10 turns, 1,000-char limit) and `VisitorSession` tracking (24-hour TTL) in `src/warrantx/agents/sessions.py` (FR-005, FR-CHAT-01, FR-ERR-19, FR-ERR-20)
- [X] T063 [P] [US2] Web: chat store, SSE client, `ChatPanel`, `MessageList`, `AssistantMessage`, `CitationChip`, `ToolTrace`, `Composer`, `SamplePrompts` in `web/src/api/sse.ts`, `web/src/state/`, `web/src/features/chat/`
- [X] T064 [P] [US2] Web: app shell (Header, DataBadge, DisclaimerBar, Footer, StatusBanner) in `web/src/features/shell/`

**Checkpoint**: chat answers about a warrant card with verified text; advice requests refused; injection canary passes.

---

## Phase 5: User Story 3 - Test "what has to go right" with scenarios (Priority: P1)

**Goal**: Scenario simulator with presets, breakeven, three-horizon curves, identical in chat and panel.
**Independent Test**: 0%/0 day/0 shift gives bid/ask - 1; +5%/3 days/-5 pts identical via panel and chat (AC-02, AC-03).

### Tests for User Story 3 (write FIRST, must FAIL)

- [X] T065 [P] [US3] Scenario identity, breakeven, intrinsic-at-expiry, range-rejection tests in `tests/unit/quant/test_scenario.py` (FR-SCN-01 to 07)
- [X] T066 [P] [US3] Contract and parity test (panel route equals chat tool output) in `tests/contract/test_scenario.py` (FR-SCN-08, AC-03)
- [X] T067 [P] [US3] Web component test for sliders with MSW mock and abort behavior in `web/tests/scenario.test.tsx` (FR-UI-20 to 22)

### Implementation for User Story 3

- [X] T068 [US3] Implement `scenario`, `curve`, `breakeven_move` and presets in `src/warrantx/quant/scenario.py`
- [X] T069 [US3] Implement scenario tool and `POST /api/scenario` sharing one function in `src/warrantx/tools/scenario.py` and `src/warrantx/api/routes/data.py`
- [X] T070 [P] [US3] Web: Scenario tab (`ScenarioSliders`, `PnlChart` with three horizons, breakeven annotation, `AssumptionsNote`, reset) in `web/src/features/scenario/`

**Checkpoint**: scenarios consistent across chat and panel.

---

## Phase 6: User Story 4 - Works any day, always shows data age (Priority: P1)

**Goal**: Replay over stored or synthetic snapshots on any day, with a collector that is rate-limited, identified and killable; badge and staleness everywhere.
**Independent Test**: Source disabled or Sunday; latest snapshot served, badge shows mode and time, sample prompts all grounded (AC-12, AC-13, AC-18).

### Tests for User Story 4 (write FIRST, must FAIL)

- [X] T071 [P] [US4] Normalization tests (percent to fraction, invalid to `None`, duplicates, crossed quotes, invalid rows) in `tests/unit/data/test_normalize.py` (FR-DATA-03, FR-ERR-07, FR-ERR-10, FR-ERR-11)
- [X] T072 [P] [US4] Collector tests with respx (pacing, backoff, kill-switch sends no request, keep last good snapshot, `suspect` on large row drop) in `tests/integration/test_collector.py` (FR-DATA-01 to 06)
- [X] T073 [P] [US4] Staleness and mode tests (stale after 20 min in market hours, market closed, sample mode) in `tests/unit/data/test_staleness.py` (FR-DATA-07, FR-ERR-02 to 04)
- [X] T074 [P] [US4] Contract tests for `/api/meta`, `/api/snapshots`, `snapshot_id` pinning and fallback in `tests/contract/test_meta.py` (FR-DATA-08, FR-ERR-21)

### Implementation for User Story 4

- [X] T075 [US4] Implement source client (identifying User-Agent, 5 s pacing, retries, parsing guard, kill-switch) in `src/warrantx/data/source_client.py`; field map from the T013 capture, else keep `# ASSUMPTION` markers; STOP and ask if terms forbid collection (Gate B)
- [X] T076 [US4] Implement normalization into `WarrantSnapshot` in `src/warrantx/data/normalize.py`
- [X] T077 [P] [US4] Implement snapshot quality checks in `src/warrantx/data/quality.py`
- [X] T078 [US4] Implement collector CLI and scheduler (five daily points, holidays, trading days) in `src/warrantx/data/collector.py`
- [X] T079 [P] [US4] Implement history providers (Yahoo `.KL` after spike T8, snapshot-derived) and realized volatility in `src/warrantx/data/history.py` and `src/warrantx/quant/vol.py`
- [X] T080 [US4] Implement mode, staleness, and public usage metrics service (visits, daily uniques, query count per FR-020), `/api/meta` and `/api/snapshots` in `src/warrantx/api/routes/meta.py`
- [X] T081 [US4] Load synthetic sample database when no snapshots exist; badge says Sample data; implement `scripts/make_fixtures.py` output wiring in `src/warrantx/data/repo.py`
- [X] T082 [P] [US4] Web: `DataBadge` states, `SnapshotPicker`, stale and degraded banners in `web/src/features/shell/`
- [X] T083 [P] [US4] Web: Data health tab (displaying mode, as-of time, staleness, collection health, and public usage metrics) in `web/src/features/health/`

**Checkpoint**: full P1 slice (US1 to US4) works offline on any day. This is the MVP.

---

## Phase 7: User Story 5 - Cited news context (Priority: P2)

**Goal**: Tavily-backed news with citations, corroboration and replay storage.
**Independent Test**: Two-domain event shows count, single-domain event is unconfirmed, empty result states none found (AC-09, AC-10).

### Tests for User Story 5 (write FIRST, must FAIL)

- [X] T084 [P] [US5] Gateway tests with respx fixtures (search, extract, empty extract, usage-limit error) in `tests/integration/test_tavily_gateway.py`
- [X] T085 [P] [US5] Corroboration, fixed 7-day window selection (FR-016), sanitization and dedupe tests in `tests/unit/news/test_news_pipeline.py` (FR-NEWS-03 to 08)
- [X] T086 [P] [US5] Stored-news replay test (news available from a stored set when Tavily is unavailable) in `tests/integration/test_news_replay.py` (constitution IX)

### Implementation for User Story 5

- [X] T087 [US5] Implement `TavilyGateway` (only module importing `tavily`; budgets, timeouts, retries, error mapping) in `src/warrantx/news/tavily_gateway.py`
- [X] T088 [P] [US5] Implement Nano structuring and validation (strict schema, URL from Tavily only) in `src/warrantx/news/structure.py`
- [X] T089 [P] [US5] Implement corroboration in `src/warrantx/news/corroborate.py` and cache plus persisted `StoredNewsSet` (strict 7-day window) in `src/warrantx/news/cache.py`
- [X] T090 [US5] Implement `search_news` tool and `GET /api/news` (fixed 7-day recency window, FR-016) in `src/warrantx/tools/news.py` and `src/warrantx/api/routes/data.py`
- [X] T091 [P] [US5] Add synthetic news fixtures labeled ILLUSTRATIVE (including an injection-canary page) in `tests/fixtures/news/`
- [X] T092 [P] [US5] Web: Sources tab (`NewsItemCard`, `EvidenceRecord`, citation-chip highlighting) in `web/src/features/sources/`

---

## Phase 8: User Story 6 - Search, stock summary and compare (Priority: P2)

**Goal**: Search, stock summary and uniform compare table without ranking.
**Independent Test**: Compare 3 warrants with identical attributes and no best label; empty stock gives explicit empty result (AC-05).

### Tests for User Story 6 (write FIRST, must FAIL)

- [X] T093 [P] [US6] Contract tests for `/api/warrants`, `/api/underlyings`, `/api/stock/{ticker}`, `/api/compare` (filters, sort, paging limits, empty stock, mixed underlyings) in `tests/contract/test_search_stock_compare.py` (FR-SRCH-*, FR-STK-*, FR-CMP-*)

### Implementation for User Story 6

- [X] T094 [US6] Implement search, stock summary (medians, flag counts, five nearest to the money) and compare tools in `src/warrantx/tools/stock.py` and `src/warrantx/tools/compare.py`
- [X] T095 [US6] Implement routes `GET /api/warrants`, `GET /api/underlyings`, `GET /api/stock/{ticker}`, `POST /api/compare` in `src/warrantx/api/routes/data.py`
- [X] T096 [P] [US6] Web: Stock tab (`WarrantTable` virtualized, filters, IV basis toggle, summary bar, group headers) in `web/src/features/stock/`
- [X] T097 [P] [US6] Web: Compare tab in `web/src/features/compare/`

---

## Phase 9: User Story 8 - Operator control (Priority: P2)

**Goal**: Operator controls, usage logs and cost report.
**Independent Test**: Cap reached gives stored/templated answer with notice; cost report totals per tier (AC-14, AC-19).

- [X] T098 [P] [US8] Test daily-cap fallback and per-session report cap with a fake clock in `tests/integration/test_budget.py` (FR-CTRL-02, FR-DEEP-05)
- [X] T099 [US8] Implement stored/templated fallback answers (passing the same verifier and linter) in `src/warrantx/guardrails/fallback.py`
- [X] T100 [P] [US8] Implement `scripts/cost_report.py` (per-day and per-tier totals from `llm_calls`)
- [X] T101 [P] [US8] Implement admin routes (including `GET /api/admin/metrics` for usage, visitor, and cost totals per FR-020, FR-023) mounted only when `WX_ADMIN_TOKEN` is set in `src/warrantx/api/routes/admin.py`
- [X] T102 [P] [US8] Implement `src/warrantx/eval/agent.py` (30 fixed prompts, deterministic assertions) and `eval/ablation.py` (all-Ultra, all-Super, tiered) for AC-19; run only with keys

---

## Phase 10: User Story 7 - Explain a move and Deep Risk Report (Priority: P3)

**Goal**: Sequential move decomposition and the Deep Risk Report.
**Independent Test**: Two snapshots a day apart sum to the total within 1e-9 with order stated; report has all parts and is reused on repeat (AC-04, AC-17).

### Tests for User Story 7 (write FIRST, must FAIL)

- [X] T103 [P] [US7] Attribution sum-to-total and missing-input tests in `tests/unit/quant/test_attribution.py` (FR-EXP-01 to 03)
- [X] T104 [P] [US7] Deep report workflow tests with `FakeLlm` (sections, red-team findings under counterpoints, same checks as chat, reuse, fallback to standard answer) in `tests/integration/test_deep_report.py` (FR-DEEP-01 to 06)

### Implementation for User Story 7

- [X] T105 [US7] Implement sequential attribution in `src/warrantx/quant/attribution.py` and `POST /api/explain-move` with tool in `src/warrantx/tools/explain.py`
- [X] T106 [US7] Implement deep report `SequentialAgent` (collector, drafter, red team, assembler), report cache and `GET /api/report/{id}` in `src/warrantx/agents/deep_report.py` and `src/warrantx/api/routes/report.py`
- [X] T107 [P] [US7] Web: Deep report button with step progress, expandable report with copy/export including disclaimer in `web/src/features/chat/DeepReport.tsx` (FR-UI-08)

---

## Phase 11: Polish and Cross-Cutting Concerns

- [X] T108 [P] Accessibility pass: axe-core on each tab in both themes, keyboard map, focus management, reduced motion in `web/tests/a11y.spec.ts` (FR-UI-07)
- [X] T109 [P] Playwright end-to-end in replay mode with the stub model (first load, stock entry, drill down, scenario change, advice refusal, source-down banner, mobile viewport) in `web/tests/e2e/`
- [X] T110 Add one named test per M and S requirement id and a traceability report script `scripts/traceability.py` that lists any unimplemented or untested requirement instead of dropping it (SC-009)
- [X] T111 [P] Run the red-team suite (advice requests, pressure variants, Malay prompts, injection canary, prompt extraction) in `tests/integration/test_redteam.py`; report zero advice leaks and zero followed injections
- [X] T112 [P] Security hardening: full-history secret scan, `.env.example` audit, confirm no raw source data or large binaries are tracked
- [X] T113 Run spike T10 (p50/p95 latency per tier), Decision Gate C (final tiers and timeouts) in `docs/DECISIONS.md`; run spikes T7 (Nebius deployment) and record `docs/DEPLOY.md`
- [X] T114 [P] Write `README.md` (what it is, the disclaimer, run instructions, license, architecture, verified vs unverified, cost table from `scripts/cost_report.py` only)
- [X] T115 Run `quickstart.md` validation end to end, confirming all performance budgets (<1.0 s quant, <3.0 s SSE status, <300 KB gzipped bundle, SC-010) and the release checklist from tech_spec Section 13

---

## Phase 12: Tavily Crawling & Deterministic Extraction (Extension to US4 & US8)

**Goal**: Implement Tavily web crawler for warrant market data collection with deterministic Python parsing, 50-credit daily budget capping, scheduled 2-3 runs/day (open, midday, close), and direct screener fallback.
**Independent Test**: Run collector with `WX_TAVILY_CRAWL=true` in live mode; verify snapshot is created with `collector_source="tavily_crawl"`, credits tracked in `Budget` (≤50), and deterministic parsing passes all quality checks without LLM extraction.

### Tests for Tavily Crawling (write FIRST, must FAIL)

- [X] T116 [P] [US4] Unit tests for deterministic HTML warrant table parser (zero LLM, golden extraction, null handling) in `tests/unit/data/test_html_parser.py` (FR-007, Principle I)
- [X] T117 [P] [US4] Integration tests for Tavily crawler client, credit cap enforcement (50 credits/day), and automatic fallback to direct screener in `tests/integration/test_tavily_crawler.py` (FR-007, FR-020)

### Implementation for Tavily Crawling

- [X] T118 [P] [US4] Implement deterministic HTML warrant table parser using BeautifulSoup in `src/warrantx/data/html_parser.py` (FR-007, Principle I)
- [X] T119 [US4] Implement Tavily web crawler client with 50-credit ceiling in `src/warrantx/data/tavily_crawler.py` (FR-007, FR-020)
- [X] T120 [US4] Update collector in `src/warrantx/data/collector.py` to default to Tavily web crawling (2–3 runs/day) with direct screener fallback, recording `collector_source` on `WarrantSnapshot` (FR-007)
- [X] T121 [US8] Add `POST /api/admin/collect` endpoint and crawl credit tracking to `GET /api/admin/metrics` in `src/warrantx/api/routes/admin.py` (FR-020, FR-023)

---

## Dependencies and Execution Order

### Phase dependencies

- **Setup (1)** then **Foundational (2)**, which blocks all stories. Spikes T009 to T011 gate T012 (Gate A); T013 gates T014 (Gate B).
- **US1 (3)** needs Foundational (fixtures T023, models T019, evidence T020).
- **US2 (4)** needs US1 (card tool) for warrant answers; verifier/linter/injection work can start right after Foundational.
- **US3 (5)** needs US1 quant modules (T035 to T037).
- **US4 (6)** needs Foundational; real-data tasks (T075, T078) need Gate B. The MVP (US1 to US4) can ship on synthetic data if Gate B chooses replay-only.
- **US5 (7)** needs T053 to T055 (Nano client) and T087 gateway; replay storage needs US4 repo.
- **US6 (8)** needs US1; **US8 (9)** needs US2; **US7 (10)** needs US2, US3.
- **Polish (11)** needs the desired stories done.
- **Tavily Crawling (12)** extends US4 and US8; builds on existing collector repo and Tavily gateway.

### Within each story

Tests first and failing, then models, services/tools, routes, then UI. Quant functions: tests (T028 to T033) before implementation (T035 to T039), per the constitution.

### Parallel opportunities

- Setup tasks T003 to T008 in parallel.
- Foundational: T015, T017, T019 to T022, T024, T025, T027 in parallel; spikes T013 and T015 alongside T009 to T011.
- US1 tests T028 to T034 together; T035, T036, T038 together; T042 and T043 together.
- US2 tests T044 to T049 together; T050 to T055 together.
- After Foundational, different stories (US1, US4, US5 verifier work) can run in parallel with different owners.

### Parallel example: User Story 1

```text
Task: "Golden-value tests in tests/unit/quant/test_bs.py"
Task: "IV round-trip tests in tests/unit/quant/test_iv.py"
Task: "Flag tests in tests/unit/quant/test_flags.py"
Task: "Implement bs.py" and "Implement iv.py" in parallel after tests fail
```

## Implementation Strategy

### MVP first

1. Phase 1 Setup, Phase 2 Foundational (run spikes early).
2. US1, then US2, US3, US4 (all P1). **STOP and validate** with `quickstart.md`: card, chat with grounding and advice boundary, scenarios, replay on any day.
3. Demo on synthetic data if Gate B keeps collection off.

### Incremental delivery

Add US5 (news), US6 (search/compare) and US8 (operator) as P2 increments, then US7 (explain move, Deep Risk Report) as P3. Each story must pass its independent test without breaking earlier stories.

## Notes

- Never commit secrets, raw scraped data or large binaries. Label illustrative values ILLUSTRATIVE.
- If a spike's pass condition fails, follow its fallback in tech_spec Section 14; if no fallback fits, stop and ask rather than guess.
- Decisions ratified: headline IV basis (mid defaulting to last-quote fallback) and license (MIT License); safety checklist gaps tracked in `checklists/safety.md`.
- Commit after each task or logical group; do not merge on red CI.
