# Feature Specification: Local-Only Plain-English Chat

**Feature Branch**: `002-local-chat` (spec directory only; no git branch or commit is created)
**Status**: Draft (input to `/speckit-plan`; run `/speckit-clarify` if any assumption below is wrong)
**Input**: "Enable the chat only in local. Do not commit git or Google Cloud. Chat gets the user query and explains in plain English. All calculation-related content is provided only with a link."

## User Stories

### US1 - Ask in plain words, get a plain-English explanation (P1)
A developer running the app on their own machine opens a chat drawer and types a question
("Is 532641 expensive to hold?", "what does gearing mean?", "why is this warrant flagged?").
The chat answers in short, jargon-free English with **no digits and no number words**.

**Acceptance**
1. Given the app runs on localhost with chat enabled, when I ask about a warrant code, the reply explains its risks qualitatively and ends with links to the views that hold the numbers.
2. Given a reply, when I scan it, it contains no figures (prices, percentages, ratios, Greeks, breakevens) other than numbers I typed myself and warrant codes.
3. Given I ask for buy/sell advice or a price prediction, the reply is the standard refusal (English or Malay).

### US2 - Every calculation is a link (P1)
Wherever a number is the real answer (holding cost, break-even, scenario P&L, comparison),
the reply gives a link that opens the existing deterministic view for that warrant.

**Acceptance**
1. Links open the X-Ray card, Scenario, Compare, Stock or Sources tab pre-loaded for the entity discussed.
2. Links are built by server code from verified evidence; the model never writes a URL.
3. News is referenced by cited link (title, domain, retrieved-at), never paraphrased with numbers.

### US3 - Local only (P1)
Chat must be unreachable and invisible in any deployed environment.

**Acceptance**
1. With `WX_CHAT_ENABLED` unset (default), `POST /api/chat` returns 404 and the UI shows no chat control.
2. With the flag on, requests that are not loopback, or that carry `X-Forwarded-For`, still return 404.
3. The Docker image and Cloud Run service are not changed by this feature.

## Functional Requirements

- **FR-LC-01** Chat is available only when `WX_CHAT_ENABLED=true` **and** the request is a direct loopback request.
- **FR-LC-02** `/api/meta` exposes `chat_enabled` so the UI renders chat only when the server says so.
- **FR-LC-03** Reply prose MUST NOT contain digits, number words, currency amounts or percentages, except user-typed numbers and warrant codes.
- **FR-LC-04** The model receives only qualitative descriptors and glossary text, never the numeric card.
- **FR-LC-05** Every reply that discusses a warrant includes at least one server-built `ViewLink`.
- **FR-LC-06** Links are same-app deep links; the app restores tab and entity from the URL.
- **FR-LC-07** Existing guardrails stay: advice intent refusal (EN/MS), injection detection, advice linter, disclaimer, rate limit, daily budget cap, session-scoped history.
- **FR-LC-08** Works in replay and sample modes, and degrades to deterministic templates if Nebius is unavailable.

## Out of Scope
- Enabling chat on Cloud Run or any hosted environment.
- Any git commit, push, or deployment.
- Deep Risk Report changes.

## Assumptions (confirmed by user on 2026-10-27)
- "Local" means the FastAPI server reached from the same machine (localhost / 127.0.0.1 / ::1), including the Vite dev server proxy.
- "Link" means an in-app deep link to the existing views, plus cited external URLs for news.
- Dates (as-of times) may appear in the UI chrome, but not in model prose.
