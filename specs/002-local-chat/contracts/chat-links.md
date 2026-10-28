# Contract: Chat Links (delta over 001 `chat-sse.md`)

Everything in [001 chat-sse.md](../../001-warrant-xray/contracts/chat-sse.md) still applies unless stated here.

## Access
`POST /api/chat` and `GET /api/sources` return **404** (not 403) unless all hold:
1. `WX_CHAT_ENABLED=true`
2. `request.client.host` is `127.0.0.1`, `::1` or `localhost`
3. Request has no `X-Forwarded-For` header

## Request (unchanged)
```json
{ "session_id": "string", "message": "1..1000 chars", "mode": "chat", "snapshot_id": null }
```
`mode: "deep"` is not enabled by this feature (returns the same 400 as an unsupported mode).

## Event changes
| Event | Change |
|---|---|
| `card` | **Not emitted** in this mode (it carries numbers) |
| `evidence` | `summary` must be digit-free (identifier + source + as_of only) |
| `token` | Verified text only; **contains no digits or number words** except user-typed numbers and warrant codes |
| `verifier` | `passed` now means "no-numbers check and advice linter passed" |
| `links` (**new**) | `{ "links": ViewLink[] }`, emitted once after the last `token`, before `done` |
| `usage` | unchanged |

### `links` payload
```json
{
  "links": [
    { "kind": "card", "label": "Open the X-Ray card", "href": "/?tab=card&code=532641&days=5",
      "entity": { "code": "532641" }, "evidence_id": "E1", "retrieved_at": null },
    { "kind": "scenario", "label": "Try a what-if scenario", "href": "/?tab=scenario&code=532641",
      "entity": { "code": "532641" }, "evidence_id": "E1", "retrieved_at": null },
    { "kind": "news", "label": "Read coverage (source site)", "href": "https://example.com/article",
      "entity": { "ticker": "MAYBANK" }, "evidence_id": "E2", "retrieved_at": "2026-10-27T15:00:00Z" }
  ]
}
```

## Deep-link grammar (SPA)
| Param | Used by | Example |
|---|---|---|
| `tab` | all | `card`, `scenario`, `compare`, `stock`, `sources`, `health` |
| `code` | card, scenario, sources | `532641` |
| `days` | card | `5` (holding days, clamped to existing 1..365) |
| `codes` | compare | `1155A1,1155B1` (2 to 4) |
| `ticker` | stock, sources | `MAYBANK` |

Unknown or invalid params are ignored and the app opens the default tab.

## Behaviour rules
- The model never supplies a URL; any URL-like text in model output is stripped by the guardrail plugin.
- If the entity cannot be resolved, the reply says so in words and links to the `stock` (screener) tab.
- Every reply ends with the code-appended disclaimer.
- Advice/prediction requests return the refusal with **no links**.

## Test obligations
- 404 matrix: flag off; flag on + non-loopback; flag on + `X-Forwarded-For`; flag on + loopback = 200 stream.
- Event order: `turn_started, status*, evidence*, token*, verifier, links, done`; no `card`.
- Digit-free assertion on concatenated `token` text across the sample prompts.
- Red-team: draft containing digits/URLs/advice is stripped, regenerated or replaced by the template.
