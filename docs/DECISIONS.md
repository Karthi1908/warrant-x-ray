# Warrant X-Ray Architecture Decisions

This document records architectural decisions, rationale, and outcomes of Decision Gates A, B, and C per `tech_spec.md` Section 1 and Section 14.

## Key Design Decisions

| ID | Decision | Rationale | Status |
|:---|:---|:---|:---|
| **D1** | Tool layer is plain async Python with Pydantic models and zero ADK imports. ADK wraps them. | Enables orchestration layer swapping (Gate A) without touching quant or business logic. | Ratified |
| **D2** | ADK runs agent loops (chat, deep report); direct Nano calls for single-shot structured tasks (entity resolution, news extraction, intent check). | Reduces turn latency, token overhead, and cost. | Ratified |
| **D3** | Verify-before-stream: display allowlist exact match + advice linter run before streaming answer tokens. | Guarantees compliance with Constitution Principle I (no unverified numbers shown). | Ratified |
| **D4** | Quant tools return both raw floats and server-formatted `display` strings; verifier exact-matches display strings. | Eliminates floating-point rounding mismatches and LLM arithmetic hallucinations. | Ratified |
| **D5** | Global guardrails enforced via ADK Plugin (`GuardrailPlugin`) and FastAPI middleware. | Single point of audit for all agents, sub-agents, and direct calls. | Ratified |
| **D6** | Nemotron reasoning content is never displayed or persisted in logs; stripped prior to client delivery. | Prevents internal chain-of-thought leakage and preserves UX cleanliness. | Ratified |
| **D7** | Chat sessions are in-memory with 2-hour idle expiry (last 10 turns); anonymous visitor deduplication via daily-salted hash. | Satisfies Constitution Principle XI (Privacy by Design) with zero user account storage. | Ratified |
| **D8** | Snapshots are append-only and immutable. Derived metrics cached by `(snapshot_id, code, params)`. | Guarantees deterministic replay and reproducible evaluation. | Ratified |

---

## Decision Gates

### Decision Gate A (Orchestration Framework)
- **Timing**: After spikes T1, T2, T3 (`T009–T011`).
- **Question**: Choose ADK + `LiteLlm`, custom `BaseLlm`, or plain loop fallback.
- **Decision**: Hybrid ADK + Direct Nano ratified. Plain async Python tool functions wrapped by ADK tool adapters with `GuardrailPlugin`. Direct single-shot calls (`warrantx.llm.direct`) for latency-critical pre-checks (intent classification, entity resolution, news fact extraction) bypassing ADK agent loop overhead.

### Decision Gate B (Data Collection Mode)
- **Timing**: After spike T6 (`T013`).
- **Question**: Live scheduled collection vs. replay-only on curated snapshots and labeled synthetic sample data.
- **Decision**: Curated Snapshots + Labeled Synthetic Replay mode selected by default. When `WX_MIBB_BASE_URL` is unset or live exchange terms disallow automated scraping, Warrant X-Ray operates deterministically in Replay and Sample modes using verified 2026-2027 Bursa calendars and synthetic fixtures (`tests/fixtures/synthetic_snapshot.json`). Live collection activates only if `WX_MIBB_BASE_URL` is explicitly provided and `WX_SOURCE_ENABLED=true`.

### Decision Gate C (Tier Mapping and Latency Budgets)
- **Timing**: After spike T10 (`T113`).
- **Question**: Final model tier assignments (Super vs Lightning for root agent; Ultra timeout and progress).
- **Decision**: Ratified 3-tier model assignment:
  1. **Nano Tier** (`nvidia/nemotron-mini-4b-instruct`): Latency p50 240ms, p95 380ms. Dedicated to intent pre-checks, entity matching, and news structuring.
  2. **Super Tier** (`nvidia/llama-3.1-nemotron-70b-instruct`): Latency p50 1.8s, p95 2.5s. Assigned as root chat reasoning model with SSE streaming status updates under 3.0s (satisfies SC-010).
  3. **Ultra / Sequential Pipeline** (Deep Risk Report): 4-stage pipeline (collect -> draft -> red-team -> assemble) with 15s per-stage timeout (total 60s hard budget). Results cached by `(code, snapshot_id, holding_days)` to avoid redundant compute. Hard daily spend budget set to $10.00 USD with rate cap at 30 queries/hour per client subnet.

