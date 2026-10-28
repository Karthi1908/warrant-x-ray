# Phase 0 Research: Local-Only Plain-English Chat

## R1 - How is chat currently disabled?
- **Finding**: Not disabled in the backend. `api/app.py` calls `app.include_router(chat_router)` unconditionally, so `POST /api/chat` is live on Cloud Run too. The SPA never mounts `ChatPanel` (App.tsx has tabs stock/card/scenario/compare/sources/health only), which is the only reason chat is "disabled".
- **Decision**: Gate server-side (flag + loopback) and let the UI follow `/api/meta.chat_enabled`.
- **Alternatives**: Vite `import.meta.env.DEV` only (rejected: leaves the production API reachable); remove router in prod (rejected: harder to test, and flag is simpler).

## R2 - Detecting "local" safely
- **Finding**: Cloud Run terminates TLS at a proxy; the app sees the proxy as `request.client` and always receives `X-Forwarded-For`.
- **Decision**: Require `request.client.host` in `{127.0.0.1, ::1, localhost}` **and** no `X-Forwarded-For`, **and** `WX_CHAT_ENABLED=true`. Vite dev proxy (`changeOrigin`) connects from loopback, so local dev passes.
- **Alternatives**: Host header check only (rejected: spoofable); env-only flag (kept as the first layer; the loopback check is defense in depth).

## R3 - How should the model be used without leaking numbers?
- **Finding**: Today `RootAgent` puts every figure (bid, ask, IV, delta, breakeven) into the prompt and relies on `verify_grounding` to allow-list them afterwards. The fallback text also prints numbers.
- **Decision**: Never give the model the numeric card. Give it deterministic qualitative phrases (D4) and glossary text. Output check becomes `verify_no_numbers`. Nano (`direct_nano_json_call`) classifies intent; Nemotron "super" tier (Nano 30B) writes the prose.
- **Alternatives**: Keep numbers in prose but verified (rejected: contradicts the requirement); ask the model "don't use numbers" with no check (rejected: unenforceable).
- **Verify in quickstart**: Nano returns valid JSON for 10 sample questions; otherwise the rules-first path handles it.

## R4 - What counts as a "number"?
- **Decision**: Reject digits, `RM` amounts, `%`, ordinal/cardinal number words (one..ninety, hundred, thousand, million, half, double, triple), and fractions. Allow: user-typed numbers echoed back, warrant codes (e.g. `532641`, `1155A1`), tickers containing digits (e.g. `99SMART`), and dates in UI chrome (not prose).
- **Risk**: Over-blocking harmless phrases ("one of the risks"). **Mitigation**: the prompt asks for phrasing without counts; template fallback guarantees an answer.

## R5 - Link shape and SPA support
- **Finding**: `App.tsx` holds `activeTab`, `currentTicker`, `compareCodes` in React state with no router and no URL sync, so there is nothing to link to today.
- **Decision**: Add a small query-string sync: `?tab=<card|scenario|compare|stock|sources|health>&code=&days=&codes=&ticker=`. Server returns relative hrefs; chat chips call the same handlers (`handleInspectWarrant`, `handleSimulateWarrant`, `handleCompareWarrants`) and update the URL so links are copyable.
- **Alternatives**: React Router (rejected: new dependency for six tabs).

## R6 - News in a no-numbers world
- **Decision**: News appears only as cited link chips (title, domain, URL, retrieved_at) from `NewsService.get_news_for_ticker`. Headline text is rendered by the UI as a link label, never inside model prose (also untrusted per Principle X).
- **Known issue (out of scope)**: `deep_report.py` calls `news_service.get_news`, which does not exist; do not copy that pattern.

## R7 - Existing guardrails to reuse
Advice intent (EN/MS), injection detection, advice linter, `strip_reasoning_traces`, disclaimer, rate limiter (30/h), `is_budget_exhausted`, session manager. All unchanged.

## R8 - Test strategy
- Unit: `verify_no_numbers` (table-driven), `describe.py`, `links.py`, gate dependency (flag off, non-loopback, `X-Forwarded-For`, loopback ok).
- Contract: SSE event order with `links`; no `card` event with numeric payload in this mode (`FakeLlm`).
- Red-team: model tries to output digits, URLs, advice; all must be stripped or refused.
- Web: chat toggle hidden when `chat_enabled=false`; link chip navigates and updates the URL.

## Post-Phase-1 Constitution Re-check
PASS on all principles. No new violations introduced by the design.
