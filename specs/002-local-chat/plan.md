# Implementation Plan: Local-Only Plain-English Chat

**Branch**: `002-local-chat` | **Date**: 2026-10-27 | **Spec**: [spec.md](spec.md)
**Builds on**: [001-warrant-xray](../001-warrant-xray/plan.md) (reuses its chat route, RootAgent, guardrails, SSE contract)

## Summary

The chat backend (`POST /api/chat`, `RootAgent`, guardrails, SSE) already exists but is hidden: the
router is registered unconditionally and the SPA never mounts `ChatPanel`. This feature (1) gates chat
to local use only, (2) changes the answer policy from "numbers verified against evidence" to
**"no numbers in prose at all; numbers live behind links"**, and (3) adds deep links so each link opens the
existing deterministic view (Card, Scenario, Compare, Stock, Sources).

Nemotron (via Nebius) only classifies the question and writes plain-English prose from qualitative
descriptors. It never sees the numeric card, so it cannot leak a figure. Links come from server code.

## Technical Context

**Language/Version**: Python 3.11 (FastAPI, Pydantic v2, google-adk, sse-starlette); TypeScript + React (Vite, Zustand)
**Primary Dependencies**: no new runtime dependencies
**Storage**: existing in-memory `ChatSession` (2h idle, last 10 turns); no message text persisted (Principle XI)
**Testing**: pytest + `FakeLlm`; Vitest + Testing Library; existing red-team suite extended
**Target Platform**: developer machine only (localhost). Docker/Cloud Run unchanged
**Constraints**: 1,000-char messages, 30 chat req/hour, 60 s turn timeout, daily LLM USD cap (all existing)
**Scale/Scope**: single local user; 1 new backend module group, 1 route change, ~5 frontend files
**Unresolved**: none blocking. Nano JSON intent output quality is verified in the quickstart (R3)

## Constitution Check (v1.1.1)

| Principle | Status | How |
|---|---|---|
| I. Numbers only from deterministic code | PASS (strengthened) | Prose contains zero numbers; verifier becomes `verify_no_numbers`; model never receives the numeric card |
| II. Every news claim cited | PASS | News surfaces only as link chips (title, domain, URL, retrieved_at); never paraphrased |
| III. Describe, never advise | PASS | Intent pre-check, linter and refusal unchanged; disclaimer appended by code |
| IV. Time and provenance | PASS with action | Reply states data mode in words ("live", "replay", "sample"); linked views show as-of. **Action**: add mode phrase to template |
| V. Pure quant engine | PASS | Untouched; links point to views computed by it |
| VI. Responsible collector | N/A | No collector change |
| VII. Tavily for news | PASS | News still via `NewsService` / `TavilyGateway` |
| VIII. Nebius + Nemotron only | PASS | `get_model("super")` and `direct_nano_json_call` only |
| IX. Always available via replay | PASS with action | Chat works over stored snapshots; **Action**: deterministic template fallback when Nebius is down or key missing |
| X. Security / untrusted input | PASS | Model cannot emit URLs (stripped); web text never enters the prompt; loopback gate |
| XI. Privacy | PASS | Session-scoped, no message persistence |

**Gate result**: PASS. Two actions folded into design. Re-check after Phase 1: PASS.

## Project Structure

### Documentation
```text
specs/002-local-chat/
├── spec.md
├── plan.md            # this file
├── research.md        # Phase 0
├── data-model.md      # Phase 1
├── quickstart.md      # Phase 1
└── contracts/
    └── chat-links.md  # Phase 1 (delta over 001 chat-sse.md)
```

### Source changes (repository root)
```text
src/warrantx/
├── config.py                      # + chat_enabled flag (default false)
├── api/
│   ├── deps.py (or chat_gate.py)  # NEW require_local_chat dependency
│   ├── app.py                     # chat router gated via dependency
│   └── routes/{chat.py, meta.py}  # chat.py: emit `links`, drop numeric `card`; meta.py: chat_enabled
├── agents/
│   ├── root.py                    # replace numeric prompt/fallback with plain-English path
│   └── prompts/system.py          # NEW plain-English, no-digits prompt
├── chat/                          # NEW package
│   ├── describe.py                # flags + thresholds -> qualitative phrases (pure)
│   ├── links.py                   # evidence -> ViewLink[] (pure)
│   └── glossary.py                # plain-English term explanations (static)
└── guardrails/
    ├── verifier.py                # + verify_no_numbers, strip_and_note reuse
    └── templates.py               # + plain-English fallback + mode phrases

web/src/
├── App.tsx                        # URL <-> state sync (tab, code, days, codes, ticker); drawer mount
├── state/chat.ts                  # handle `links` event; stop storing numeric card
├── api/sse.ts                     # parse `links`
└── features/chat/{ChatPanel,AssistantMessage,LinkChip}.tsx

tests/ (unit + contract + red-team) and web/tests/
```

## Design Decisions

- **D1 Local gate (two layers)**: `WX_CHAT_ENABLED` (default `false`) and a dependency that returns 404 unless
  the client host is loopback **and** no `X-Forwarded-For` header is present (Cloud Run always adds one). The
  flag is never baked into the image (`.env*` is in `.dockerignore`).
- **D2 UI visibility**: SPA reads `chat_enabled` from `/api/meta`; if false the toggle is not rendered.
  Single source of truth, so a production bundle can never show chat.
- **D3 No-numbers policy**: `verify_no_numbers` rejects digits, number words (one..ninety, hundred, half...),
  `RM` amounts and `%`, allowing only user-typed numbers and warrant codes. On failure: regenerate once, then
  strip-and-note, then deterministic template.
- **D4 Qualitative descriptors**: `describe.py` converts existing flags (WIDE_SPREAD, DEEP_OTM, ISSUER_MISMATCH,
  near expiry, high gearing) and `config/flags.yaml` thresholds into phrases. The model is given phrases plus glossary text only.
- **D5 Links**: `links.py` builds relative deep links from evidence; the model's URLs are stripped by the guardrail plugin.
- **D6 Intent**: `direct_nano_json_call` (currently unused) classifies `{intent, code, ticker, term}`; rules-first regex/underlying
  matching stays as fallback so chat works with no key.
- **D7 Deep links in SPA**: add lightweight query-string sync (no router dependency): `?tab=card&code=532641&days=5`.

## Out of Scope / Not Changed
Cloud Run service, Dockerfile, git history, Deep Risk Report, quant engine, ingestion.
