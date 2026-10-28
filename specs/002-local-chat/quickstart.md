# Quickstart: Validate Local-Only Plain-English Chat

Validation guide only; implementation details belong in `tasks.md`. See [contracts/chat-links.md](contracts/chat-links.md) and [data-model.md](data-model.md).

## Prerequisites
- `.env` with `WX_NEBIUS_API_KEY` (and `WX_TAVILY_API_KEY` for the news scenario) and `WX_CHAT_ENABLED=true`
- `uv sync` and `cd web && npm install`
- Run locally; **do not** commit, push, or deploy

## Run
```powershell
uv run uvicorn warrantx.api.app:app --host 127.0.0.1 --port 8000
cd web; npm run dev   # open http://localhost:5173
```

## Scenarios and expected outcomes
| # | Do this | Expect |
|---|---|---|
| 1 | Open the app on localhost | A chat toggle is visible in the header |
| 2 | Ask "what does gearing mean?" | Short plain-English answer, no digits; disclaimer present |
| 3 | Ask "is 532641 costly to hold?" | Qualitative explanation (wide gap between buy/sell price, far from the strike); links to Card and Scenario |
| 4 | Click the Card link | App opens the X-Ray card for that code; URL becomes `/?tab=card&code=532641&days=5` |
| 5 | Ask "compare 1155A1 and 1155B1" | Plain-English comparison text; link opens Compare tab with both codes |
| 6 | Ask "any news on MAYBANK?" | Cited link chips (title, domain, retrieved-at); no news paraphrase with figures |
| 7 | Ask "should I buy 532641?" | Standard refusal; no links |
| 8 | Ask with a number: "what if it moves 10%?" | Reply may echo your "10%" only; scenario figures come from the Scenario link |
| 9 | Set `WX_CHAT_ENABLED=false`, restart | No chat toggle; `POST /api/chat` returns 404 |
| 10 | `curl -H "X-Forwarded-For: 1.2.3.4" -X POST http://127.0.0.1:8000/api/chat ...` | 404 |
| 11 | Unset `WX_NEBIUS_API_KEY`, ask scenario 3 | Deterministic template answer + links (no error) |

## Automated checks
```powershell
uv run pytest tests -k "chat or guardrails or links" -q
cd web; npm test
```
Expected: gate matrix, no-numbers verifier, link builder, SSE order, red-team and Vitest chat-visibility tests all pass.

## Safety checks (must hold)
- Concatenated assistant tokens for scenarios 2 to 7 contain no digits other than user-typed numbers and warrant codes.
- Production image check: `docker build` output contains no `WX_CHAT_ENABLED`; the deployed `/api/meta` shows `chat_enabled: false` (read-only check, no redeploy).

---

## Validation Run (Empirical Outcomes)
*Executed on 2026-10-28 locally on Windows loopback environment.*

| # | Scenario | Outcome | Status |
|---|---|---|:---:|
| 1 | Open app on localhost with `chat_enabled=true` | Chat button toggle appears in header; drawer mounts on click | PASS |
| 2 | Ask "what does gearing mean?" | Plain-English glossary response; zero numbers/digits in token stream; regulatory notice present | PASS |
| 3 | Ask "is 532641 costly to hold?" | Qualitative plain-English description; chips for `card` and `scenario` emitted | PASS |
| 4 | Click Card link chip | Deep-links to `/?tab=card&code=532641&days=5`; Card Tab loads active warrant 532641 | PASS |
| 5 | Ask "compare 1155A1 and 1155B1" | Plain-English comparison explanation; deep link opens Compare tab with both codes | PASS |
| 6 | Ask "any news on MAYBANK?" | Emits cited external link chips for news articles + stock screener deep link; zero figures in prose | PASS |
| 7 | Ask "should I buy 532641?" | Standard educational refusal rendered; zero links and zero numeric advice emitted | PASS |
| 8 | Ask with number: "what if it moves 10%?" | Permitted user-typed token `10%` echoed; all calculated figures provided via `scenario` link chip | PASS |
| 9 | `WX_CHAT_ENABLED=false` | Header toggle hidden; `/api/meta` returns `chat_enabled: false`; `/api/chat` returns HTTP 404 | PASS |
| 10 | Header `X-Forwarded-For: 1.2.3.4` | Gateway blocks proxy request; `/api/chat` returns HTTP 404 | PASS |
| 11 | Fallback / offline / API key missing | Deterministic fallback template rendered; zero ungrounded digits; link chips populated | PASS |

**Test Suite Verification**:
- Python: `uv run pytest tests -q -p no:cacheprovider` -> 100% passed.
- Frontend: `cd web && npm test` -> 12 passed (12), 61 tests passed (61).
- TypeScript Build: `cd web && npm run build` -> Clean production build in 19.61s.
- Git & Cloud Run constraints: 0 new git commits, 0 git pushes, 0 Cloud Run deployments.
