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
- **Timing**: After spikes T1, T2, T3.
- **Question**: Choose ADK + `LiteLlm`, custom `BaseLlm`, or plain loop fallback.
- **Decision**: Pending execution of spikes T009–T011.

### Decision Gate B (Data Collection Mode)
- **Timing**: After spike T6 (`T013`).
- **Question**: Live scheduled collection vs. replay-only on curated snapshots and labeled synthetic sample data.
- **Decision**: Pending execution of spike T013 (`scripts/spikes/t6_capture.py`).

### Decision Gate C (Tier Mapping and Latency Budgets)
- **Timing**: After spike T10 (`T113`).
- **Question**: Final model tier assignments (Super vs Lightning for root agent; Ultra timeout and progress).
- **Decision**: Pending execution of spike T113.
