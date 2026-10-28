# Tasks: Local-Only Plain-English Chat

**Input**: Design documents from `/specs/002-local-chat/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/chat-links.md](contracts/chat-links.md), [quickstart.md](quickstart.md)

**Tests**: Included. The plan (research R8) and the constitution ("CI stays green") call for them.
**Hard rules for this feature**: do **not** git commit/push and do **not** deploy to Google Cloud. Cloud Run, `Dockerfile` and `.dockerignore` stay unchanged.

## Format: `- [ ] [TaskID] [P?] [Story?] Description with file path`
- **[P]** = different files, no dependency on an incomplete task
- **[US1]** plain-English explanation, **[US2]** calculations as links, **[US3]** local-only gate

---

## Phase 1: Setup

- [X] T001 Add `chat_enabled: bool = False` (env `WX_CHAT_ENABLED`) to `Settings` in `src/warrantx/config.py`
- [X] T002 [P] Add `WX_CHAT_ENABLED=false` with a "local development only" comment to `.env.example`
- [X] T003 [P] Create package `src/warrantx/chat/__init__.py` (empty module docstring)
- [X] T004 [P] Record the baseline: run `uv run pytest tests -k "chat or guardrails" -q` and note current pass/fail (no code change)

---

## Phase 2: Foundational (blocks all user stories)

**Purpose**: pure, reusable building blocks used by US1, US2 and US3.

- [X] T005 [P] Write table-driven tests for `verify_no_numbers` in `tests/unit/guardrails/test_no_numbers.py` (digits, `RM` amounts, `%`, number words, fractions rejected; user-typed numbers, warrant codes like `532641`/`1155A1`, tickers like `99SMART` allowed)
- [X] T006 Implement `NumberCheckResult` and `verify_no_numbers(text, allowed_tokens)` in `src/warrantx/guardrails/verifier.py` (reuse `strip_and_note`)
- [X] T007 [P] Write unit tests for descriptors and links in `tests/unit/chat/test_describe_links.py` (create `tests/unit/chat/__init__.py`): flags map to digit-free phrases; link hrefs match the deep-link grammar; unknown code yields the `stock` fallback link
- [X] T008 [P] Implement static plain-English glossary (gearing, spread, IV, theta, delta, break-even, moneyness, expiry) in `src/warrantx/chat/glossary.py`; all text digit-free
- [X] T009 [P] Implement `ChatDescriptor` builder in `src/warrantx/chat/describe.py` using existing flags and thresholds from `config/flags.yaml` (`load_flags()`); output phrases only, never figures
- [X] T010 [P] Implement `ViewLink` model and builders (`card`, `scenario`, `compare`, `stock`, `sources`, `health`, `news`) in `src/warrantx/chat/links.py` per [contracts/chat-links.md](contracts/chat-links.md)
- [X] T011 [P] Add digit-free plain-English fallback templates and mode phrases ("live", "replay", "sample" in words) to `src/warrantx/guardrails/templates.py`
- [X] T012 [P] Add plain-English, no-digits system prompt (`PLAIN_ENGLISH_SYSTEM_PROMPT`) to `src/warrantx/agents/prompts/system.py` (describe never advise; no numbers; point to links; under ~120 words)

**Checkpoint**: building blocks tested; no behavior change yet.

---

## Phase 3: User Story 3 - Local only (P1) 🔒 do first (safety)

**Goal**: chat is unreachable and invisible unless explicitly enabled on a direct loopback request.
**Independent Test**: flag off -> 404 and no UI control; flag on + loopback -> works; flag on + `X-Forwarded-For` or non-loopback -> 404.

- [X] T013 [P] [US3] Write the 404 matrix tests in `tests/unit/api/test_chat_gate.py` (create `tests/unit/api/__init__.py`): flag off; flag on + non-loopback; flag on + `X-Forwarded-For`; flag on + loopback passes; applies to both `/api/chat` and `/api/sources`
- [X] T014 [US3] Implement `require_local_chat` dependency (404 `NotFoundError`) in `src/warrantx/api/chat_gate.py`
- [X] T015 [US3] Apply the dependency to the chat router in `src/warrantx/api/app.py` (`include_router(chat_router, dependencies=[Depends(require_local_chat)])`)
- [X] T016 [US3] Add `chat_enabled` (true only if flag on and request is local) to the `/api/meta` response model and handler in `src/warrantx/api/routes/meta.py`
- [X] T017 [US3] Read `chat_enabled` from `/api/meta` into app state in `web/src/App.tsx` (no UI mount yet; used by US2 task T031)
- [X] T018 [US3] Verify deployment artifacts are untouched: confirm `Dockerfile` and `.dockerignore` contain no `WX_CHAT_ENABLED` and `.env*` is still excluded (read-only check)

**Checkpoint**: US3 complete and independently testable; production behavior is "chat 404".

---

## Phase 4: User Story 1 - Plain-English explanation (P1) 🎯 MVP

**Goal**: replies are short, jargon-free, advice-free and contain no numbers.
**Independent Test**: scenarios 2, 3, 7, 8, 11 in [quickstart.md](quickstart.md); concatenated tokens contain no digits other than user-typed numbers and warrant codes.

- [X] T019 [P] [US1] Write SSE contract tests in `tests/contract/test_chat_plain_english.py` using `FakeLlm`: event order `turn_started, status*, evidence*, token*, verifier, done`; no `card` event; token text digit-free across sample prompts
- [X] T020 [P] [US1] Write red-team tests in `tests/unit/guardrails/test_chat_redteam.py`: model draft with digits, with a URL, with buy/sell advice, and a prompt-injection message are stripped, regenerated, or replaced by the template
- [X] T021 [P] [US1] Implement intent classification in `src/warrantx/chat/intent.py`: call `direct_nano_json_call` (in `src/warrantx/llm/direct.py`) for `{intent, code, ticker, term}` with rules-first fallback (existing regex and underlying matching); no key or error -> fallback
- [X] T022 [US1] Add a plain-English turn path to `src/warrantx/agents/root.py`: advice and injection pre-checks, classify, resolve entities, build `ChatDescriptor`, draft with `get_model("super")` using `PLAIN_ENGLISH_SYSTEM_PROMPT`, advice linter, `verify_no_numbers`, regenerate once, then strip-and-note, then template. Remove the numeric-card prompt and numeric fallback strings from this path
- [X] T023 [US1] Strip URL-like text from model output in `src/warrantx/guardrails/plugin.py` (the model must not supply links)
- [X] T024 [US1] Update `src/warrantx/guardrails/fallback.py` (budget-exhausted path) to return the digit-free template instead of numeric factual output
- [X] T025 [US1] Update `src/warrantx/api/routes/chat.py`: use the plain-English turn, stop emitting `card` events, emit digit-free `evidence` summaries (identifier, source, as-of only), set `verifier.passed` from the no-numbers and linter checks
- [X] T026 [US1] Add the data-mode phrase (live/replay/sample in words) to every warrant-related reply in `src/warrantx/agents/root.py` (Constitution IV action)

**Checkpoint**: chat answers in plain English with no numbers; MVP usable via the API on localhost.

---

## Phase 5: User Story 2 - Every calculation is a link (P1)

**Goal**: each reply that discusses a warrant ends with working deep links; the SPA opens the right view from the URL; chat UI shows link chips.
**Independent Test**: scenarios 3, 4, 5, 6 in [quickstart.md](quickstart.md).

- [X] T027 [P] [US2] Write contract test for the `links` event (emitted once after the last `token`, before `done`; advice refusal has no links) in `tests/contract/test_chat_links.py`
- [X] T028 [P] [US2] Write Vitest for deep links in `web/tests/deeplink.test.tsx`: loading `/?tab=card&code=532641&days=5` opens the card tab; invalid params fall back to the default tab; clicking a link chip updates the URL
- [X] T029 [US2] Add `links` to the turn result and emit the `links` SSE event in `src/warrantx/agents/root.py` and `src/warrantx/api/routes/chat.py` (built by `src/warrantx/chat/links.py`)
- [X] T030 [US2] For news intent, fetch via `NewsService.get_news_for_ticker` and return cited `news` links (title, domain, URL, retrieved_at) only, never prose, in `src/warrantx/agents/root.py`
- [X] T031 [P] [US2] Parse the `links` event and add types in `web/src/api/sse.ts`
- [X] T032 [US2] Store links per assistant message and ignore any `card` event in `web/src/state/chat.ts`
- [X] T033 [P] [US2] Create `web/src/features/chat/LinkChip.tsx` (label, kind icon, external-link marker for `news`)
- [X] T034 [US2] Render link chips and update the footer copy (remove "Figures computed deterministically" wording that implies numbers in chat) in `web/src/features/chat/AssistantMessage.tsx`
- [X] T035 [P] [US2] Replace sample prompts with plain-English, no-number prompts in `web/src/features/chat/SamplePrompts.tsx`
- [X] T036 [US2] Add query-string sync (`tab`, `code`, `days`, `codes`, `ticker`) to `web/src/App.tsx`: parse on load, update on tab/entity change, ignore invalid values
- [X] T037 [US2] Mount a chat drawer and header toggle in `web/src/App.tsx` and `web/src/features/shell/Header.tsx`, rendered only when `chat_enabled` is true; chip click calls the existing `handleInspectWarrant` / `handleSimulateWarrant` / `handleCompareWarrants` handlers
- [X] T038 [US2] Update `web/tests/chat.test.tsx` and `web/tests/shell.test.tsx`: chat toggle hidden when `chat_enabled=false`, visible when true; chips render for a `links` event

**Checkpoint**: full flow works locally: ask, read plain-English answer, click link, see the numbers in the existing view.

---

## Phase 6: Polish & Cross-Cutting

- [X] T039 [P] Update the README release note (chat is local-only, off by default, numbers via links) in `README.md`
- [X] T040 Run full checks: `uv run pytest tests -q` and `cd web; npm test; npm run build` (type check); fix regressions
- [X] T041 Walk through [quickstart.md](quickstart.md) scenarios 1 to 11 locally and record results in `specs/002-local-chat/quickstart.md` (append a "Validation run" section)
- [X] T042 Final safety review: grep that no digits/URLs can reach `token` events, `git status` shows no commit made by this feature, no Cloud Run deployment was run

---

## Dependencies & Execution Order

- **Phase 1** -> **Phase 2** (blocks all stories).
- **US3 (Phase 3)** first: it is small and makes the rest safe. No dependency on US1/US2 beyond Phase 2.
- **US1 (Phase 4)** depends on Phase 2 only (works via API once US3 flag is on locally).
- **US2 (Phase 5)** depends on US1 (links ride on the new turn path) and on US3 T016/T017 (`chat_enabled`).
- **Polish** after all stories.

Within a story: tests -> pure modules -> agent/route -> UI.

### Parallel opportunities
- Phase 1: T002, T003, T004
- Phase 2: T005, T007, T008, T009, T010, T011, T012 (different files)
- US3: T013 alongside nothing else; T014 then T015/T016 sequential (shared `app.py`/meta)
- US1: T019, T020, T021 together; T022 to T026 sequential (same files: `root.py`, `chat.py`)
- US2: T027, T028, T031, T033, T035 together; T029 to T038 touch shared files, keep ordered

### Example: Phase 2 in parallel
```text
Task: T005 tests in tests/unit/guardrails/test_no_numbers.py
Task: T008 glossary.py   Task: T009 describe.py   Task: T010 links.py
Task: T011 templates.py  Task: T012 prompts/system.py
```

## Implementation Strategy

1. **MVP = Phase 1 + 2 + US3 + US1**: local-only, plain-English, no numbers (usable through the API).
2. Add **US2** for links and the chat drawer UI (completes the requested experience).
3. Polish and validate with the quickstart. Stop there: **no commit, no deploy**.

## Notes
- All assumptions in new code are marked `# ASSUMPTION` (constitution agent rules).
- Never pass the numeric `WarrantCard` into any prompt.
- Known unrelated bug (do not copy): `deep_report.py` calls `news_service.get_news`, which does not exist.
