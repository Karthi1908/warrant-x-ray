# Implementation Plan: Warrant X-Ray

**Branch**: `001-warrant-xray` | **Date**: 2026-10-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-warrant-xray/spec.md`; technical design from [tech_spec.md](../../tech_spec.md); detailed functional requirements from [requirements.md](../../requirements.md).

## Summary

Warrant X-Ray is a chat-first risk copilot for Bursa structured warrants. A deterministic core (stored snapshots, a pure-function quant engine, flags) produces every number. A thin agentic layer (Google ADK driving NVIDIA Nemotron models on Nebius Token Factory) only selects tools and explains results. Tavily provides cited news over a strict 7-day recency window and serves as the default automated web crawler for warrant market data (parsed deterministically via Python with no LLM arithmetic), with the direct HTTP screener endpoint as secondary fallback. Answers are verified (exact string match against server-formatted display strings, advice linter in English and Malay) *before* any text is streamed. A Vite + React single-page app shows chat plus an evidence panel. The app runs every day in replay mode over stored or synthetic snapshots.

Technical approach comes from `tech_spec.md`; Phase 0 research ([research.md](research.md)) records which decisions are settled and which are blocked on verification spikes T1 to T10.

## Technical Context

**Language/Version**: Python 3.11+ (ADK needs 3.10+); TypeScript (strict) for the web app; exact versions pinned by `uv lock` and `package-lock.json` at milestone M0 (not guessed here)

**Primary Dependencies**: `google-adk` (+ LiteLLM extra), `openai` SDK (direct single-shot calls), `tavily-python` (`AsyncTavilyClient`), FastAPI, Pydantic v2, `sse-starlette`, SQLAlchemy 2 + aiosqlite, NumPy/SciPy, httpx, tenacity, rapidfuzz, structlog, `beautifulsoup4` (for deterministic HTML parsing of crawled warrant tables); web: Vite, React, Tailwind, Radix, TanStack Query/Table/Virtual, Zustand, Recharts, `@microsoft/fetch-event-source`, `openapi-typescript`/`openapi-fetch`

**Storage**: SQLite (WAL) behind a repository interface; snapshot and usage metrics tables append-only; in-memory `ChatSession` (2-hour idle expiry, last 10 turns); ephemeral `VisitorSession` (`X-Session-ID`, 24h TTL) for anonymous visit tracking; placement on Nebius is VERIFY (T7)

**Testing**: pytest, pytest-asyncio, hypothesis, respx, a `FakeLlm` (`BaseLlm` subclass) for offline ADK flow tests; Vitest, Testing Library, MSW, Playwright, axe-core; `live`-marked manual smoke/eval tests

**Target Platform**: Linux container (multi-stage Docker) on a Nebius serverless endpoint (VERIFY T7); browsers desktop and mobile

**Project Type**: web application (Python backend serving a built SPA) plus collector and eval CLIs from the same image

**Performance Goals**: pure quant engine computation for up to 300 warrants (with 5 IV bases per row) under 1.0 s on 1 CPU core; streaming chat emits its first status event within 3.0 s of request; scenario slider result within 300 ms of response (SC-007); initial client JavaScript bundle under 300 KB gzipped (SC-010)

**Constraints**: 60 s per chat turn; 1,000-char messages; 30 chat requests/hour/client; daily LLM USD cap and Tavily credit cap (200 credits total, with 50 credits allocated for 2-3 daily warrant crawl runs and 150 credits reserved for news); no accounts or personal data; anonymous visit tracking via `VisitorSession` UUIDs (24h expiry) and daily-salted one-way cryptographic hash of client subnet/User-Agent; no raw scraped data or secrets in the public repo; all LLM calls Nemotron on Nebius; all news search via Tavily over strict 7-day window; advice/prediction requests declined in English and Malay (FR-017); headline IV basis defaults to `mid`, falling back to `last` if quotes are missing; `risk_free_rate: 0.03` configured in `config/flags.yaml` (default 0.03 fallback)

**Scale/Scope**: single always-on instance, a few hundred warrants per stock, hackathon-scale traffic; 10 UI areas (shell, chat, Stock, Card, Scenario, Compare, Sources, Data health) and 13 API route groups (including public meta and operator admin metrics)

**Unresolved (tracked, not guessed)**: Nemotron/Token Factory tool-call and reasoning behavior (T1, T9); ADK + LiteLLM compatibility (T2, T3); model IDs, limits, prices (T4); Tavily coverage of Malaysian sources (T5); source response format, ratio direction, terms of use (T6, OI-01 to OI-05); Nebius deployment features (T7); Yahoo `.KL` history (T8); latency tiers (T10). These are research tasks, not blockers for design.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Evaluated against constitution v1.1.0.

| Principle | Status | How the design satisfies it |
|---|---|---|
| I. Numbers only from deterministic code | PASS | Tools return raw values plus server-formatted `display` strings (D4); verifier exact-matches display strings before streaming (D3); LLM never rounds or converts. Tavily crawling fetches raw HTML, parsed 100% deterministically via Python code without LLM extraction. |
| II. Every news claim cited | PASS | `NewsItem` carries `url`, `domain`, `published_date`, `retrieved_at` from Tavily, never from model output; empty result yields an explicit "no sources found". |
| III. Describe, never advise | PASS | Advice-intent pre-check, linter (English + Malay), templated refusal, disclaimer appended by code. |
| IV. Time and provenance transparency | PASS | `as_of` + `mode` + `collector_source` on every response and the data badge; stale marker; unknown values as `null`. |
| V. Pure quant engine | PASS | `quant/` has no I/O, clock, network or LLM; `as_of` passed in; tests-first. |
| VI. Responsible collector | PASS (gated) | Identifying User-Agent, scheduled 2-3 times/day (open, midday, close), 50-credit ceiling, retries/backoff, `WX_SOURCE_ENABLED` kill-switch, cache. Tavily crawl is primary, direct screener is fallback. `raw_json` lives only in the git-ignored DB. |
| VII. Tavily search & crawl | PASS | Only `news/tavily_gateway.py` and `data/tavily_crawler.py` import `tavily`; key from env; crawl and search budgeted atomically (50 crawl / 150 search); content treated as untrusted. |
| VIII. Nebius + Nemotron only | PASS | `llm/models.py` and `llm/direct.py` target Token Factory; startup check against `/v1/models`; the fake model is test-only. |
| IX. Always available via replay | PASS with action | Synthetic fixtures give replay data. **Action**: the tech spec's `news_cache` only holds 30 minutes, so replay needs a persisted, snapshot-keyed news store plus synthetic news fixtures labeled ILLUSTRATIVE (see research R11, data-model `StoredNewsSet`). |
| X. Security and untrusted input | PASS | Env-var secrets, raw web text never reaches Super/Ultra, tools take no model-supplied URLs, canary-injection tests. |
| XI. Privacy by design | PASS with action | No accounts; in-memory `ChatSession` (2h idle expiry, last 10 turns); ephemeral `VisitorSession` (24h UUID) for visit counting without raw IP storage; `evidence`, `llm_calls` store hashed session ids and **no message text**. **Action**: keep user message text out of persisted tables and logs beyond the optional 80-char truncation. |

Agent rules: `# ASSUMPTION` markers for assumptions, VERIFY items never treated as fact, tests before quant functions, stop and ask on unverifiable unknowns (enforced by decision gates A to C).

**Gate result**: PASS. No unjustified violations; two actions folded into the design (rows IX, XI). Re-check after Phase 1: PASS (see bottom of [research.md](research.md)).

## Project Structure

### Documentation (this feature)

```text
specs/001-warrant-xray/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── rest-api.md
│   └── chat-sse.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/warrantx/
├── config.py
├── quant/            # bs, iv, metrics, scenario, attribution, flags, vol, ratio (pure)
├── data/             # source_client, normalize, repo, history, quality, collector
├── tools/            # ADK-agnostic async tools + evidence formatting
├── llm/              # models (LiteLlm factories, fallback), direct (Nano calls), pricing, usage
├── news/             # tavily_gateway, structure, corroborate, cache, chatter
├── agents/           # app, root, deep_report, prompts/
├── guardrails/       # plugin, verifier, linter, injection, intent, templates
├── api/              # app, deps, errors, ratelimit, budget, sse, routes/
└── eval/             # agent, ablation, model_fit runners

config/               # flags.yaml, prices.yaml, sources.yaml, linter_patterns.yaml, samples.yaml, bursa_holidays.yaml
scripts/              # make_fixtures.py, cost_report.py, smoke.py
tests/
├── unit/             # quant, data, guardrails
├── integration/      # agent flow with FakeLlm, respx clients
├── contract/         # OpenAPI validation
└── fixtures/         # synthetic snapshots and news (ILLUSTRATIVE)

web/
├── src/              # api, state, features/{chat,stock,card,scenario,compare,sources,health,shell}, ui, lib, styles
└── tests/            # vitest, playwright (e2e + axe)

docs/                 # DECISIONS.md, VERIFIED.md, DEPLOY.md, FEEDBACK.md
Dockerfile  docker-compose.yml  pyproject.toml  uv.lock  .env.example  LICENSE  README.md
```

**Structure Decision**: Web application as a single Python package (`src/warrantx`) plus a separate `web/` SPA built into the same container. Layering follows tech_spec decision D1: `quant` and `tools` have no ADK imports; `agents` and `guardrails/plugin.py` are the only ADK-aware modules, so the orchestration layer can be swapped (Gate A) without touching business logic. `LICENSE` is the open-source MIT License.

## Complexity Tracking

> No constitution violations to justify. Deliberate complexity is listed for transparency.

| Choice | Why Needed | Simpler Alternative Rejected Because |
|--------|------------|-------------------------------------|
| ADK + custom guardrail plugin | Tool loop, sub-agent deep report, one audit point for guardrails | A plain loop is the planned fallback (Gate A), but ADK is the user's chosen orchestration |
| Verify-then-stream (D3) | Constitution I forbids ever showing an unverified number | Streaming drafts would expose unverified figures; kept only as an off-by-default experiment flag |
| Direct Nano calls beside ADK (D2) | Single-shot extraction/matching is cheaper and easier to test | Running them as agents adds overhead without benefit |
| Persisted snapshot-keyed news store | Constitution IX requires replay to include Tavily results | A 30-minute cache cannot support weekend/outage replay |
