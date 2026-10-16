# Contract: Chat Stream (SSE over POST)

`POST /api/chat` returns `text/event-stream`. Browsers cannot use `EventSource` with POST, so the client uses `@microsoft/fetch-event-source`.

## Request

```json
{
  "session_id": "string (client-created, kept in sessionStorage)",
  "message": "string, 1 to 1000 characters",
  "mode": "chat | deep",
  "snapshot_id": "integer | null"
}
```

## Events (in order of occurrence)

| Event | Data | Notes |
|---|---|---|
| `turn_started` | `{turn_id}` | |
| `status` | `{step, text}` | Text from a static per-tool map, never from model text (FR-CHAT-03) |
| `tool_call` | `{name, args}` | Arguments redacted to allowed fields |
| `evidence` | `{evidence_id, kind, source, as_of, summary}` | Summary built server-side |
| `card` | `WarrantCard` or `StockSummary` | Panel opens automatically (FR-UI-03) |
| `token` | `{text}` | **Verified text only**, emitted after grounding and advice checks (D3) |
| `verifier` | `{passed, retried, removed_sentences}` | Feeds the grounding pass-rate record (FR-GRD-03) |
| `usage` | `{model, tier, in_tokens, out_tokens, latency_ms, cost_usd}` | One per call, from the logged `llm_calls` |
| `done` | `{turn_id}` | End of turn |
| `error` | `{code, message, recoverable}` | Partial grounded text may precede it (FR-ERR-17) |

Event ids increase monotonically per turn.

## Behavior rules

- Answer text is buffered, verified, then streamed in short chunks. Status, evidence and cards stream live.
- Pure advice or prediction requests get the templated refusal without invoking the agent (FR-ADV-01); the disclaimer is appended by code to every answer.
- A 15-second comment heartbeat keeps proxies from closing idle streams; headers `Cache-Control: no-cache`, `X-Accel-Buffering: no`.
- Client disconnect cancels the running turn and records partial usage.
- No mid-turn resume; the client shows a retry control on `error` or lost connection.
- Turn limit 60 s; on timeout return the grounded part so far with a partial notice.
- Answer order: answer, numbers, flags and context, limits, disclaimer (FR-CHAT-04). Each factual sentence carries an `[E#]` marker linked to evidence (FR-CHAT-05).
- Deep mode streams `status` per pipeline step (collect, draft, review, assemble); on failure it falls back to a standard answer and says so (FR-DEEP-06).

## Test obligations

- Event order, heartbeat, cancel on disconnect, error mapping, and verified-before-stream behavior using `FakeLlm`.
- Red-team suite: advice requests (including pressure and Malay), canary-token injection pages, prompt-extraction attempts.
