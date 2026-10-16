# Warrant X-Ray - Technical Specification

Oct 13, 2026 and @Karthik

This document specifies how Warrant X-Ray is built: Google ADK orchestrating NVIDIA Nemotron models on Nebius Token Factory, Tavily for news, a pure-Python quant core, and a Vite and React front end. It pairs with the Functional Specification, which defines what the system must do.

## 1. Technology Decisions at a Glance

**Verification basis (2026-10-13).** Items marked *Verified* were read in current vendor documentation or vendor-published pages. Items marked *VERIFY* are plausible but unconfirmed and are tracked as tasks T1 to T10 in Section 14. A coding agent MUST NOT treat a VERIFY item as fact.

| Area | Decision | Basis |
| --- | --- | --- |
| Orchestration | Google ADK for Python (`google-adk`): `LlmAgent` with tools, `SequentialAgent` for the deep report, a `Runner` with an `App`, and a plugin for global guardrails | Verified: ADK documents `LlmAgent`, workflow agents, `Runner`, `InMemorySessionService`, `App` and plugins; supports Python 3.10 or newer |
| LLM gateway | Nebius Token Factory through its OpenAI-compatible API at `https://api.tokenfactory.nebius.com/v1/` with a bearer API key | Verified in Nebius quickstart and function-calling docs |
| Model adapter | ADK `LiteLlm` wrapper with the `openai/` prefix and `api_base` set to Token Factory | Verified pattern: ADK documents `LiteLlm` for non-Gemini and OpenAI-compatible endpoints. Compatibility with Nemotron tool calls is VERIFY (T2) |
| Models | Nemotron Nano (30B, 3B active), Super (120B, 12B active), Ultra (550B, 55B active); optional Nemotron 3.5 Lightning (30B) as a fast agent tier | Verified as listed on Nebius; exact IDs, context sizes and tool-call behavior are VERIFY (T1, T4) |
| News and web | Tavily Python SDK, `AsyncTavilyClient`: search (topic news, time filters, domain filters), extract, optional crawl and research | Verified in Tavily docs |
| API | FastAPI with Pydantic v2; Server-Sent Events over POST for chat | Standard; no vendor dependency |
| Quant | NumPy and SciPy, pure functions, no I/O | Standard |
| Storage | SQLite (WAL mode) through SQLAlchemy 2 and aiosqlite behind a repository interface | Decision; persistence on Nebius is VERIFY (T7) |
| Front end | Vite, React, TypeScript (strict), Tailwind, Radix primitives, TanStack Query and Table, Zustand, Recharts, `@microsoft/fetch-event-source` | Decision; see Section 10 |
| Packaging | `uv` with a lockfile, Docker multi-stage image, GitHub Actions | Decision |

### Key design decisions

| ID | Decision | Reason |
| --- | --- | --- |
| D1 | The tool layer is plain async Python functions with Pydantic models and no ADK imports. ADK wraps them. | The orchestration framework can be swapped without touching business logic if ADK and Nemotron prove incompatible (T2). |
| D2 | ADK runs the agent loops that need tool selection (chat, deep report). Single-shot structured tasks (name matching fallback, news fact extraction, advice-intent check) use a direct model call, not an agent. | Less overhead, simpler tests, cheaper. |
| D3 | Answers are verified before text is streamed. Tool progress, evidence and cards stream live; answer text is buffered, checked, then streamed. | Guarantees that no unverified number is ever shown, which is a hard rule of the product. A flag allows draft streaming for latency experiments. |
| D4 | Tools return both raw values and server-formatted display strings. The model is told to copy display strings verbatim, and the verifier matches strings exactly. | Exact string matching is more reliable than floating-point tolerance. |
| D5 | Guardrails live in one ADK plugin plus API-layer checks, so every agent and sub-agent is covered. | One place to audit. |
| D6 | Nemotron models are reasoning models: reasoning content is never shown or logged, token budgets leave room for it, and reasoning effort is configurable per tier. | Avoids truncated answers and leaking internal text. Behavior on Token Factory is VERIFY (T1, T9). |
| D7 | Sessions use ADK's in-memory session service with a 2-hour expiry and a single always-on instance. | Matches the privacy requirement (no stored chat) and keeps the system simple. |
| D8 | Snapshots are append-only and immutable. Everything derived is recomputed or cached by `(snapshot_id, code, params)`. | Makes replay and evaluation reproducible. |

### Evidence base consulted

- Nebius Token Factory [quickstart](https://docs.tokenfactory.nebius.com/quickstart.md) and [function calling](https://docs.tokenfactory.nebius.com/ai-models-inference/function-calling): base URL, OpenAI SDK compatibility, tool format, `tool_choice` values.
- Nebius [Nemotron models page](https://nebius.com/services/token-factory/models/nvidia-nemotron-models-inference): Lightning, Ultra, Super and Nano listed with tool calling and reasoning in the live catalog.
- A Nebius API [issue from May 2026](https://github.com/nebius/api/issues/211) reporting that reasoning traces consumed small token budgets and tool calls returned 400 errors through the OpenAI wrapper. The vendor page above now lists tool calling, so the two conflict and must be settled by test (T1).
- ADK [callbacks reference](https://adk.dev/callbacks/types-of-callbacks/) and [vLLM and LiteLlm model guide](https://adk.dev/agents/models/vllm/index.md).
- Tavily [search best practices](https://docs.tavily.com/documentation/best-practices/best-practices-search) and [Python SDK reference](https://docs.tavily.com/sdk/reference/python).

## 2. Architecture and Runtime Topology

The system has a deterministic core (data, quant, tools) and a thin agentic layer on top. The diagram is plain text so a coding agent can read it directly.

```text
  Browser (Vite + React SPA)
     |  REST (JSON)                 |  POST /api/chat  (SSE stream)
     v                              v
  +--------------------------- FastAPI app (one container) ----------------------------+
  |  middleware: request id, CORS, rate limit, budget guard, structured logging        |
  |                                                                                    |
  |  routes/data  ----------------> repository + quant engine + flags (no LLM)         |
  |                                                                                    |
  |  routes/chat --> turn_runner --> ADK Runner (App: warrantx)                        |
  |                      |             |                                               |
  |                      |             +-- root LlmAgent  (Super tier, tool loop)      |
  |                      |             |      tools: resolve_entity, search_warrants,  |
  |                      |             |      get_warrant, price_scenario, compare,    |
  |                      |             |      explain_move, stock_summary, news,       |
  |                      |             |      data_health                              |
  |                      |             +-- deep_report SequentialAgent (Ultra tier)    |
  |                      |             +-- GuardrailPlugin (all agents)                |
  |                      v                                                             |
  |              verifier + linter -> regenerate once or strip -> stream tokens        |
  |                                                                                    |
  |  llm/ gateway: LiteLlm -> Nebius Token Factory (Nano | Super | Ultra), fallback   |
  |  news/ gateway: Tavily (search, extract) -> Nano structuring -> corroboration      |
  +---------------------------------------+------------------------------------------+
                                          |
                  SQLite (snapshots, rows, history, evidence, llm_calls, news_cache)
                                          ^
                                          |  append-only writes
  Collector (python -m warrantx.collector) -- Maybank GetScreenerData -- scheduled
  Eval jobs (python -m warrantx.eval ...)  -- run on demand, write eval/results
```

### Processes

| Process | Entry point | Notes |
| --- | --- | --- |
| API and web | `uvicorn warrantx.api.app:app` | Serves the built SPA from `web/dist` and the JSON and SSE API. Single instance in MVP (in-memory sessions, in-process caches). |
| Collector | `python -m warrantx.collector --once` or a scheduler loop | Same image, different command. Writer of snapshots. |
| Evals | `python -m warrantx.eval.<name>` | Runs prompts and ablations; writes JSON results. |

If the platform cannot run a scheduled job against shared storage, the collector runs as a scheduler inside the API container (decision recorded in Section 7).

### Chat turn lifecycle

1. Validate the request (length, session id), apply rate limit and the daily budget guard. Reject early with the correct SSE `error` event.
2. Advice-intent pre-check: rules first, a Nano call only if ambiguous. A pure advice request gets the templated refusal without running the agent.
3. Create or fetch the ADK session (in memory), set state: `snapshot_id`, `mode`, `as_of`.
4. Run the root agent through `Runner.run_async`. Map ADK events to SSE events as in the table below.
5. Collect the final answer text without streaming it; run the verifier and linter.
6. On failure, send one corrective message into the same session and re-run; on a second failure strip offending sentences and add the omission note.
7. Stream the verified text as `token` events, emit `verifier` and `usage` events, then `done`.
8. Persist the turn's evidence and `llm_calls` rows. Release the session slot.

### ADK event to SSE event mapping

| ADK observation | SSE event | Notes |
| --- | --- | --- |
| Model response containing a function call | `tool_call` and `status` | Status text comes from a static map per tool name, never from model text |
| Function response from a tool | `evidence`, and `card` when the tool is `get_warrant` | Evidence summary is built server-side |
| Partial text events | none | Buffered (decision D3) |
| Final response text | buffered, then `token` events after verification |  |
| Exception or timeout | `error` with `recoverable` | Partial grounded content may be returned (functional rule on 60-second limit) |

### Time and concurrency

- All server code is async. Blocking work (IV solving over many rows) runs in a thread pool with a bounded size.
- A turn has a 60 second wall-clock limit (`asyncio.timeout`). A model call has a per-tier timeout (Section 5).
- A global semaphore limits concurrent model calls (default 8) to stay inside provider rate limits (T4).

## 3. Backend Stack and Project Structure

**Rule:** exact versions are chosen at milestone M0 by running `uv lock`, then pinned in the lockfile. This document does not state version numbers because they were not checked. Python 3.11 or newer is recommended (ADK requires 3.10 or newer).

### Dependencies

| Group | Packages | Purpose |
| --- | --- | --- |
| Orchestration | `google-adk` and the extra that provides LiteLLM support (check the ADK install docs; one documented form is `google-adk[extensions]`) | Agents, runner, sessions, `LiteLlm` |
| LLM access | `litellm` (pulled by ADK extras), `openai` (for direct single-shot calls and the fallback adapter) | Token Factory access |
| Web search | `tavily-python` | Search and extract |
| API | `fastapi`, `uvicorn`, `sse-starlette`, `pydantic`, `pydantic-settings` | HTTP, SSE, validation, config |
| HTTP | `httpx`, `tenacity` | Collector client and retries |
| Data | `sqlalchemy`, `aiosqlite`, `rapidfuzz`, `pyyaml`, optionally `yfinance` | Storage, name matching, config, history |
| Math | `numpy`, `scipy` | Pricing and solving |
| Logging | `structlog` | JSON logs |
| Dev | `pytest`, `pytest-asyncio`, `hypothesis`, `respx`, `ruff`, `mypy`, `pre-commit`, `pip-audit` | Quality gates |

Every new dependency needs a one-line justification in `docs/DECISIONS.md` and a license check.

### Package layout

```text
src/warrantx/
  config.py                 # pydantic-settings; loads YAML from config/
  quant/                    # pure functions, no I/O
    bs.py  iv.py  metrics.py  scenario.py  attribution.py  flags.py  vol.py
  data/
    source_client.py        # Maybank GetScreenerData client (httpx)
    normalize.py            # raw row -> WarrantSnapshot
    repo.py                 # repository interface + SQLite implementation
    history.py              # HistoryProvider: yfinance, snapshot-derived
    quality.py              # snapshot quality checks
    collector.py            # CLI and scheduler
  tools/                    # ADK-agnostic async functions
    registry.py             # tool name -> function + status text + schema
    evidence.py             # Evidence wrapper and display formatting
    warrants.py  scenario.py  compare.py  explain.py  stock.py  news.py  health.py  entity.py
  llm/
    models.py               # tier -> LiteLlm factories, fallback chain
    direct.py               # single-shot structured calls (Nano) via openai client
    pricing.py  usage.py    # cost computation and llm_calls logging
  news/
    tavily_gateway.py  structure.py  corroborate.py  cache.py  chatter.py
  agents/
    app.py                  # builds ADK App, Runner, session service
    root.py                 # root LlmAgent
    deep_report.py          # SequentialAgent workflow
    prompts/                # instruction templates as .md files
  guardrails/
    plugin.py               # ADK BasePlugin
    verifier.py  linter.py  injection.py  intent.py  templates.py
  api/
    app.py  deps.py  errors.py  ratelimit.py  budget.py  sse.py
    routes/ meta.py data.py chat.py report.py
  eval/                     # ablation, agent eval, model-fit runners
config/                     # flags.yaml  prices.yaml  sources.yaml  linter_patterns.yaml  samples.yaml
```

### Configuration

- `pydantic-settings` loads environment variables with the prefix `WX_` and validates at startup; the app refuses to start with a clear message if a required value is missing.
- YAML files in `config/` hold thresholds, domain lists, price tables and linter patterns. They are validated against Pydantic models at startup.
- Required in `live` mode: `WX_NEBIUS_API_KEY`, `WX_TAVILY_API_KEY`. In `replay` mode with `WX_LLM_STUB=true`, neither is required.

### Coding rules specific to this stack

- Tools never import `google.adk`. Adapters in `agents/` wrap them.
- No module-level mutable state except the loaded settings and the HTTP clients created in the app lifespan.
- Clients (Tavily, Nebius, HTTP) are created once in the FastAPI lifespan and injected.
- All timestamps are timezone-aware UTC internally; Malaysia time is applied only at display.
- Every external call has an explicit timeout, a retry policy and a mapped error type.
- Public functions in `quant/` have `mypy --strict` clean signatures and docstrings that state units.

## 4. Agent Orchestration with Google ADK

ADK is used for what it does well: a tool-calling loop, session state, workflow agents and lifecycle callbacks. Business logic stays outside it (decision D1). Statements about ADK behavior are tagged *Verified* (seen in current ADK docs or examples) or *VERIFY* (to confirm in task T3 before relying on them).

### Agent hierarchy

```text
App(name='warrantx', plugins=[GuardrailPlugin])
  root_agent: warrantx_root        LlmAgent, Super tier, tool loop, max 6 model rounds
      tools (FunctionTool wrappers over tools/*):
        resolve_entity  search_warrants  get_warrant  price_scenario
        compare_warrants  explain_move  stock_summary  search_news  data_health
  deep_report: SequentialAgent     only when mode == 'deep'
      1 evidence_collector         LlmAgent, Super tier, same tools, writes state['temp:bundle']
      2 drafter                    LlmAgent, Ultra tier, output_schema=RiskReport, no tools
      3 red_team                   LlmAgent, Ultra tier, output_schema=Counterpoints, no tools
      4 assembler                  plain Python step (merge, verify, lint)
Not agents (direct calls): entity fallback match (Nano), news fact extraction (Nano),
                           advice-intent check (Nano), Tavily search and extract
```

Why this shape: a single root agent with tools keeps the chat predictable. The deep report is a fixed pipeline, which `SequentialAgent` fits. News retrieval is a deterministic pipeline inside a tool, so it needs no agent.

### Model assignment

Each agent receives its own model object from `llm/models.py` (Section 5). The tier is configuration, not code.

```python
from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

root = LlmAgent(
    name='warrantx_root',
    model=models.for_tier('super'),          # LiteLlm or fallback wrapper
    instruction=prompts.root_instruction,     # callable or template; injects as_of and mode
    tools=registry.adk_tools(),               # FunctionTool wrappers
    generate_content_config=cfg_for('super'), # temperature, max_output_tokens
)
app = App(name='warrantx', root_agent=root, plugins=[GuardrailPlugin(settings)])
runner = Runner(app=app, session_service=InMemorySessionService())
```

*Verified:* `App`, `Runner(app=..., session_service=...)`, `InMemorySessionService`, `InMemoryRunner`, and `runner.run_async(...)` yielding events appear in current ADK documentation. *VERIFY (T3):* the exact keyword names for `LlmAgent` model config in the installed version.

### Tools

- Each tool is an `async` Python function with full type hints and a docstring written for the model. ADK derives the function declaration from them.
- Tools return a dict with `evidence_id`, `kind`, `as_of`, `data` (raw values) and `display` (server-formatted strings). The model is told to copy `display` strings (decision D4).
- **Avoid default parameter values and rely on required parameters or `Optional[...] = None`.** Some ADK paths do not carry defaults into function declarations (VERIFY, T3). State the default in the docstring and apply it inside the function.
- A tool never raises into the loop. It returns `{error: <code>, message: <text>}`.
- Evidence for the turn is stored in session state under a `temp:` key (VERIFY, T3, that `temp:` keys are not persisted and are visible to callbacks); if not, use a `contextvars` store keyed by invocation id.

```python
async def get_warrant(code: str, holding_days: int, tool_context: ToolContext) -> dict:
    '''Return the Warrant Card for one warrant code. holding_days is 1 to days left; use 5 if the user gave none.'''
    snap_id = tool_context.state.get('snapshot_id')
    card = await cards.build(code=code, holding_days=holding_days, snapshot_id=snap_id)
    return evidence.wrap(kind='card', payload=card, tool_context=tool_context)
```

### Callbacks and the guardrail plugin

*Verified:* `LlmAgent` supports `before_model_callback(callback_context, llm_request)`, `after_model_callback(callback_context, llm_response)`, `before_tool_callback(tool, args, tool_context)`, plus after-tool and agent-level callbacks. Parameter names must match exactly because ADK passes them by keyword. Callbacks may be sync or async and may be lists. Plugins extending `BasePlugin` apply to every agent, tool and model call in the runner.

| Hook | What it does in this project |
| --- | --- |
| before agent | Checks the daily budget and rate limit; stores `turn_id` in state |
| before model | Enforces output token cap and history trimming; marks untrusted content wrappers; refuses if the session is over the model-call cap |
| after model | Logs usage to `llm_calls`; strips reasoning content from any text part; records latency |
| before tool | Validates arguments with Pydantic; enforces at most 8 tool calls per turn; rejects any tool that takes a URL from the model |
| after tool | Wraps the result as Evidence; adds its display strings and numbers to the turn allowlist; caps payload size |
| after agent | Runs nothing heavy; the verifier runs in the API layer so it can trigger a re-run |

Returning a value from a before-callback short-circuits the step (used for budget and cap refusals). Details of the verifier are in Section 11.

### Sessions

- One ADK session per browser session id (hashed). State keys: `snapshot_id`, `mode`, `as_of`, `holding_days_default`, `temp:*` for per-turn data.
- `InMemorySessionService` has no expiry, so a small janitor task deletes sessions idle for 2 hours. Run a single API instance (decision D7). A restart loses sessions, which is acceptable and matches the privacy rule.
- A corrective regeneration message is added to the same session with a marker so it can be excluded from later history.

### Deep Risk Report workflow

- `SequentialAgent` passes data through session state using each agent's `output_key`.
- ADK limits an agent that uses `output_schema`: such an agent cannot also call tools (VERIFY, T3). The design already follows this: tool use is confined to `evidence_collector`; `drafter` and `red_team` only read the evidence bundle from state and emit JSON.
- If Token Factory does not honor JSON-schema response formats for a given Nemotron model (T1), instruct JSON in the prompt, parse with Pydantic, and allow one automatic repair call.
- Progress events (`status`) are emitted when each step starts. Ultra calls get a longer timeout than chat calls.
- Cache the assembled report by `(code, snapshot_id, holding_days)`.

### Streaming configuration

- Run the root agent in a non-streaming mode for text so that final text arrives as one event (VERIFY, T3, the `RunConfig` streaming option name and behavior). Function-call events still arrive between model rounds and drive `tool_call` and `status` events.
- The API layer, not ADK, streams the verified text to the browser.

### Failure and fallback

| Problem | Response |
| --- | --- |
| ADK with `LiteLlm` mishandles Nemotron tool calls | Replace the model adapter with a small `BaseLlm` subclass that calls the OpenAI SDK directly (T2) |
| ADK itself blocks progress | Swap the orchestration layer for a plain loop that calls the same `tools/registry` functions; no business logic changes (decision D1) |
| A tier errors repeatedly | Fallback chain defined in Section 5 |

## 5. Nebius Token Factory and NVIDIA Nemotron Integration

### Connection (Verified)

| Item | Value |
| --- | --- |
| Base URL | `https://api.tokenfactory.nebius.com/v1/` |
| Authentication | `Authorization: Bearer <API key>`; key created in the Token Factory console |
| Protocol | OpenAI-compatible chat completions; works with the OpenAI SDK |
| Tool calling | OpenAI function-calling format. The model returns tool-call instructions; the application executes them and returns `role: tool` messages. `tool_choice` accepts `auto` (default) or an explicit function object. |
| Model IDs | Include the publisher namespace and are case-sensitive; list them with `GET /v1/models` |

The API key stays on the server. It is read from `WX_NEBIUS_API_KEY` and never reaches the browser, logs or the image.

### Model catalog (confirm every row with the live model list, T1 and T4)

| Tier | Candidate ID (as seen in public sources) | Size | Context as listed | Role |
| --- | --- | --- | --- | --- |
| Nano | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | 30B, 3B active | 262K | Entity fallback, news fact extraction, advice-intent check |
| Super | `nvidia/nemotron-3-super-120b-a12b` | 120B, 12B active | 256K | Chat tool loop, evidence collection |
| Ultra | `nvidia/Nemotron-3-Ultra-550b-a55b` | 550B, 55B active | 256K on one catalog page, 1,024K on another (conflict) | Deep report drafting and red team |
| Fast agent (optional) | `nvidia/Nemotron-3_5-Lightning` | 30B hybrid MoE | 1,024K as listed | Candidate replacement for Super in the chat loop if it is faster and equally accurate |

IDs above come from vendor pages and third-party projects, not from a live call. The app MUST read `/v1/models` at startup, verify that each configured ID exists, and fail with a clear message if not. `/api/meta` reports the resolved IDs.

### Model factory (ADK adapter)

```python
from google.adk.models.lite_llm import LiteLlm

def lite_llm_for(tier: str) -> LiteLlm:
    t = settings.tiers[tier]                       # id, max_tokens, timeout_s, reasoning_effort
    return LiteLlm(
        model=f'openai/{t.id}',                    # openai/ prefix selects the OpenAI-compatible route
        api_base=settings.nebius_base_url,         # https://api.tokenfactory.nebius.com/v1/
        api_key=settings.nebius_api_key,
        max_tokens=t.max_tokens,
        timeout=t.timeout_s,
        num_retries=2,
        temperature=t.temperature,
    )
```

*Verified:* ADK documents `LiteLlm(model=..., api_base=..., api_key=...)` for OpenAI-compatible endpoints. *VERIFY (T2):* that extra keyword arguments such as `timeout`, `num_retries` and a request-body extension for reasoning effort are passed through, and that a model ID containing two slashes resolves correctly after the `openai/` prefix.

ADK's `LiteLlm` has had open issues about message-role handling for some models and endpoints, so pin the ADK and LiteLLM versions in the lockfile and run the integration test in T2 on every upgrade.

### Reasoning models: required handling

The Nemotron models on Token Factory are reasoning models. A May 2026 Nebius issue reported that small token budgets were consumed by reasoning, and that tool calls returned 400 errors through the OpenAI wrapper. Nebius' current model page lists tool calling and reasoning for these models, so the report may be outdated. Treat both as true until T1 settles it.

- **Token budget.** Set `max_tokens` high enough to cover reasoning plus the answer (start at 4096 for chat turns, 2048 for Nano extraction) and measure actual usage before lowering.
- **Reasoning effort.** A third-party catalog note says Token Factory accepts `reasoning_effort` of low, medium or high on some models. Use low for Nano and for tool-selection turns, medium for final synthesis, and confirm support per model (T1).
- **Never expose reasoning.** If a response includes a reasoning field or think tags, strip it in the after-model hook before verification and display. Do not log reasoning text, only token counts.
- **Temperature.** 0 to 0.2 for tool turns and extraction; up to 0.3 for synthesis. Tool arguments must be reproducible.

### Capability smoke matrix (task T1, run in M0)

For each candidate model, record pass or fail and the observed latency for:

| Test | Expected |
| --- | --- |
| Plain chat, small `max_tokens` | Non-empty answer, reasoning not leaking into content |
| One tool with `tool_choice=auto` | A well-formed tool call with valid JSON arguments |
| Two tools in one turn (parallel calls) | Both calls returned, or sequential behavior documented |
| Tool result fed back | Final answer uses the tool output |
| `tool_choice` forced to a named function | The named function is called |
| Streaming on and off, with tools | Behavior documented; tool-call deltas assemble correctly |
| JSON-schema response format | Valid JSON, or fallback to prompt-based JSON |
| Reasoning effort low, medium, high | Latency and token use per level |
| Long prompt (50K tokens) | Accepted; latency noted |

Results go into `docs/VERIFIED.md` and drive the tier assignments above.

### Routing and parameters

| Task | Tier | Temp | Max tokens | Timeout | Notes |
| --- | --- | --- | --- | --- | --- |
| Advice-intent check | Nano | 0 | 256 | 10 s | Only when rules are ambiguous |
| Entity disambiguation | Nano | 0 | 512 | 10 s | Pick among given candidates, JSON only |
| News fact extraction | Nano | 0 | 1024 | 20 s | Strict JSON schema; one article per call |
| Chat loop | Super | 0.1 | 4096 | 30 s per call | Max 6 rounds, 60 s per turn |
| Deep report: collect | Super | 0.1 | 4096 | 30 s per call | Same tools |
| Deep report: draft and red team | Ultra | 0.2 | 6000 | 90 s | Run asynchronously with progress events |

### Resilience

- **Retries:** exponential backoff with jitter on HTTP 429 and 5xx, at most 2 retries per call. Never retry on 4xx other than 429.
- **Fallback chain:** Ultra to Super to Nano to templated answer. Implemented as a `FallbackLlm` subclass of ADK's `BaseLlm` that tries each wrapped model in order (VERIFY, T3, the `BaseLlm` method signature in the installed version).
- **Circuit breaker:** after 3 consecutive failures for a tier, skip it for 60 seconds.
- **Concurrency:** one global semaphore (default 8) in front of all model calls; excess requests queue, then time out with a friendly message.
- **Startup check:** one 1-token call per configured tier with a short timeout; failures mark the tier degraded in `/api/meta`.

### Usage and cost

- Read token counts from each response's usage block (prompt and completion; record reasoning tokens if reported).
- Compute cost from `config/prices.yaml`, which holds USD per million input and output tokens per model and the date confirmed. Prices MUST be confirmed on the Nebius pricing page on the day of any published evaluation (T4).
- Write one `llm_calls` row per call: timestamp, turn id, session hash, model, tier, purpose, tokens, latency, cost, status.
- The daily USD cap is checked before each turn and before each Ultra call.

### Single-shot structured calls

Nano tasks use a thin `llm/direct.py` client (OpenAI SDK, same base URL) with: JSON-schema response format where supported, otherwise prompt-enforced JSON; Pydantic validation; one repair retry; and the same usage logging. This avoids agent overhead for one-step jobs.

### Testing without the network

- `FakeLlm` (a `BaseLlm` subclass) replays scripted tool calls and final texts so the ADK flow, callbacks and API are tested offline and in CI.
- Live tests are marked `live`, need keys, and are run manually: the T1 matrix and a 30-prompt agent eval.

## 6. Tavily Integration

### What is verified about the API

- The Python SDK offers `TavilyClient` and `AsyncTavilyClient`; this project uses the async client.
- `search` accepts `query` (keep it under 400 characters), `search_depth` (ultra-fast, fast, basic, advanced), `topic` (general, news, finance), `time_range` (day, week, month, year) or `start_date` and `end_date`, `include_domains` and `exclude_domains` (wildcards allowed), `max_results`, and `include_raw_content`. With topic news, results include `published_date`. Advanced depth costs 2 credits; separate focused queries are recommended over one broad query; several searches can run concurrently with `asyncio.gather`.
- `extract` accepts `urls` (up to 20), `extract_depth`, an optional `query` and `chunks_per_source` (1 to 5).
- `crawl` (root URL, depth, breadth, limit, instructions, path filters) and `research` (input, model mini, pro or auto, streaming, `output_schema`, `citation_format`) also exist.
- The SDK raises `InvalidAPIKeyError` and `UsageLimitExceededError`. A free tier of 1,000 credits per month exists.
- **VERIFY (T5):** domain coverage for the Malaysian sources, presence of `published_date` for them, whether extraction works on exchange announcement pages, credit use reported per call, and rate limits.

### Gateway

`news/tavily_gateway.py` is the only module that imports `tavily`. It provides:

```python
class TavilyGateway:
    async def search_news(self, query: str, *, days: int, domains: list[str], depth: str, max_results: int) -> list[RawHit]: ...
    async def extract(self, urls: list[str], *, query: str | None) -> list[RawPage]: ...
    def credits_used_today(self) -> int: ...
```

| Concern | Rule |
| --- | --- |
| Client | One `AsyncTavilyClient` created in the app lifespan; key from `WX_TAVILY_API_KEY` |
| Time window | For 1 to 7 days use `time_range` day or week; for longer windows use `start_date` and `end_date` |
| Depth | `advanced` for the primary news query; `basic` for the Malay fallback and for chatter |
| Domains | From `config/sources.yaml`, per language; confirm each returns results (T5) |
| Query building | Company name plus ticker, under 400 characters, one topic per query; fan out up to 3 queries concurrently |
| Retries | Retry transient network errors and 5xx twice with backoff; never retry authentication or usage-limit errors |
| Error mapping | `UsageLimitExceededError` and invalid key map to a `news_unavailable` result; the chat continues without news |
| Budget | Daily credit cap (`WX_TAVILY_DAILY_CREDITS`); per turn at most 1 search batch of up to 3 queries and 3 extracts |
| Timeouts | 15 seconds per search, 25 seconds per extract |

### Pipeline inside the `search_news` tool

1. **Search.** Concurrent English queries; add Malay queries only if fewer than 3 English results.
2. **Rank and select.** Drop duplicates by URL; keep the 8 most relevant; mark candidates that look like exchange announcements or long articles.
3. **Extract.** Call `extract` for up to 3 selected URLs. If a page returns empty content, record `extraction_failed` and fall back to the snippet.
4. **Structure (Nano).** One call per item turns text into a `NewsItem` using a strict schema. Raw text is discarded afterward.
5. **Validate and sanitize.** Pydantic validation; drop items that fail; strip URLs and markup from facts; cap lengths; remove facts matching injection patterns.
6. **Corroborate.** Group items about the same event and count distinct domains.
7. **Cache and return.** Store in `news_cache` for 30 minutes; return at most 6 items plus the display strings the model may quote.

```yaml
NewsItem:
  title: str                       # max 200 chars
  url: str                         # from Tavily result, never from model output
  domain: str
  published_date: date | null      # Tavily value; else parsed from text; else null (shown as undated)
  retrieved_at: datetime
  event_type: earnings | contract | dividend | director_dealing | corporate_action | regulatory | macro | other
  facts: list[str]                 # max 3, each max 160 chars, no URLs
  stated_numbers: list[{label: str, text: str}]   # as written in the source
  corroboration_count: int
  unconfirmed: bool                # true when exactly one domain
  extraction_method: search_snippet | tavily_extract
```

### Corroboration rule

Two items describe the same event when they share the ticker and event type, fall within 2 days of each other, and either have title similarity of 0.8 or higher or share at least one stated number. Count distinct registered domains in each group. One domain means `unconfirmed`.

### Optional Tavily features (behind flags, after the MVP)

| Flag | Feature | Use |
| --- | --- | --- |
| `WX_TAVILY_RESEARCH` | `research` endpoint with an `output_schema` | Background brief inside the Deep Risk Report; credit-heavy, cap strictly; every claim still needs a source link |
| `WX_TAVILY_CRAWL` | `crawl` of a configured announcements listing | Only if T5 shows listing pages are crawlable and terms allow it |
| `WX_FEATURE_CHATTER` | Forum search on configured domains | Low-confidence context only (functional spec); same gateway, `basic` depth |

### Prompt-injection controls for web content

- Raw Tavily content never reaches Super or Ultra. Only validated `NewsItem` objects do.
- The Nano extraction prompt states that the input is untrusted data and that only the JSON schema may be output; free-text fields are short, so there is little room for hidden instructions.
- After validation, facts that match patterns such as instructions to ignore rules, mentions of system prompts, role-play requests, or URLs are dropped and counted in the Data health tab.
- A canary test places a hidden instruction and a unique token in a mock page and asserts that the final answer contains neither.

### Tests

- Unit: query building, window selection, corroboration, sanitization.
- Recorded fixtures (via `respx`) for search and extract responses, including an empty extract and a usage-limit error.
- One live smoke test per release, marked `live`, with the credit cost recorded.

## 7. Data Collector, Storage and Replay

### Source client (`data/source_client.py`)

The Maybank Warrants site is a client-rendered app that calls a `GetScreenerData` endpoint (field names inferred from the page script; confirmed only after task T6). The collector talks to that endpoint directly with `httpx`; it does not run a browser unless T6 shows the endpoint is not usable.

| Aspect | Specification |
| --- | --- |
| Request | HTTP POST, form-encoded, to the base URL read from `WX_MIBB_BASE_URL` plus `GetScreenerData`; the init call sends `token` and `init=1`, the query call sends the filter parameters listed in the functional spec |
| Headers | Identifying `User-Agent` with project name and contact; `Accept: application/json` |
| Timeouts | Connect 5 s, read 20 s, total 30 s |
| Pacing | At least 5 s between any two requests; one bulk query per snapshot |
| Retries | 3 attempts with exponential backoff on network errors and 5xx; respect `Retry-After` on 429; no retry on other 4xx |
| Parsing | Require `status == 'SUCCESS'` and a list under the data key; otherwise record failure and keep the last good snapshot |
| Kill-switch | `WX_SOURCE_ENABLED=false` makes the client refuse to send any request |
| Tests | `respx` fixtures built from the synthetic generator; a manual live capture script writes to a git-ignored folder |

An undocumented, unauthenticated-looking endpoint can change or be restricted without notice. The terms-of-use check (T6) comes before any scheduled collection.

### Normalization (`data/normalize.py`)

- One Pydantic model, `WarrantSnapshot`, with field aliases mapped from source keys. Unknown keys go to `raw`.
- Validators convert units from the data dictionary: percent to fraction, thousands volumes to units, strings to dates. Invalid or non-positive values become `None`.
- The exercise-ratio field is stored as `ratio_raw`; the derived `shares_per_warrant` is computed in `quant/` after the convention test (functional requirement on ratio direction).
- A last-traded price and time are stored if the source provides them. If not, they are `None` and the last-traded IV basis shows `unknown` (T6).
- Rows failing validity rules (non-positive strike or underlying price) are stored with `valid=false` and excluded from lists.

### Schema (SQLite)

```sql
CREATE TABLE snapshots (
  id INTEGER PRIMARY KEY,
  fetched_at TEXT NOT NULL,            -- UTC ISO 8601
  source_last_update TEXT,
  row_count INTEGER NOT NULL,
  ok INTEGER NOT NULL,
  note TEXT,
  quality_json TEXT                    -- null rates, crossed quotes, duplicates, row-count change
);
CREATE TABLE warrant_rows (
  snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
  code TEXT NOT NULL,
  issuer TEXT, type TEXT, underlying_ticker TEXT, expiry_date TEXT,
  strike REAL, ratio_raw REAL, underlying_bid REAL,
  bid REAL, ask REAL, bid_volume REAL, ask_volume REAL, traded_volume REAL,
  last_price REAL, last_time TEXT,
  issuer_iv REAL, issuer_eg REAL, issuer_delta REAL, issuer_premium REAL,
  issuer_theta_raw REAL, sensitivity_ticks REAL, moneyness TEXT,
  indicators_json TEXT, valid INTEGER NOT NULL DEFAULT 1,
  raw_json TEXT NOT NULL,
  PRIMARY KEY (snapshot_id, code)
);
CREATE INDEX idx_rows_underlying ON warrant_rows(snapshot_id, underlying_ticker);
CREATE TABLE underlyings (ticker TEXT PRIMARY KEY, code TEXT, name TEXT, updated_at TEXT);
CREATE TABLE price_history (ticker TEXT, day TEXT, close REAL, source TEXT, PRIMARY KEY (ticker, day));
CREATE TABLE evidence (id TEXT PRIMARY KEY, turn_id TEXT, kind TEXT, source TEXT, as_of TEXT, payload_json TEXT);
CREATE TABLE llm_calls (
  id INTEGER PRIMARY KEY, ts TEXT, turn_id TEXT, session_hash TEXT, model TEXT, tier TEXT,
  purpose TEXT, in_tokens INTEGER, out_tokens INTEGER, reasoning_tokens INTEGER,
  latency_ms INTEGER, cost_usd REAL, status TEXT
);
CREATE TABLE news_cache (key TEXT PRIMARY KEY, created_at TEXT, payload_json TEXT);
CREATE TABLE budgets (day TEXT, kind TEXT, used REAL, PRIMARY KEY (day, kind));
CREATE TABLE reports (key TEXT PRIMARY KEY, created_at TEXT, report_json TEXT);
```

- SQLite runs in WAL mode with foreign keys on. The collector is the only writer to snapshot tables; the API writes only evidence, calls, cache, budgets and reports.
- Snapshot tables are append-only (decision D8). The `raw_json` column is never exposed by the API.
- Dates use the budget day in Malaysia time; stored timestamps are UTC.

### Snapshot quality checks (`data/quality.py`)

Run on every snapshot and store the result in `quality_json`:

- Row count against the previous good snapshot; a drop of more than 30 percent marks the snapshot `suspect` and keeps the previous one as current.
- Null rate per field; count of crossed quotes (bid above ask), duplicate codes and invalid rows.
- Share of rows whose recomputed effective gearing is within tolerance of the issuer value (a quick sanity check that the ratio convention is still right).
- Results are shown on the Data health tab.

### Scheduling

- Times are in Malaysia time (`Asia/Kuala_Lumpur`): before the open, mid-morning, midday, mid-afternoon and after the close, on trading days only. A holiday calendar lives in `config/bursa_holidays.yaml` (source and sessions to be confirmed, T6).
- **Preferred:** a Nebius Serverless Job on a schedule writing to shared storage. **MVP default:** the scheduler runs inside the API container (APScheduler or a simple asyncio loop) with the endpoint kept at one always-on instance. If the endpoint scales to zero, scheduled collection would stop, so confirm always-on support first (T7).
- Storage placement options to evaluate in T7, in order of simplicity: (A) collector inside the API container with a local volume; (B) a Job writing a SQLite or Parquet file to S3-compatible object storage that the API loads at start and refreshes; (C) a managed database. Record the choice in `docs/DECISIONS.md`.

### Underlying price history

- `HistoryProvider` interface with two implementations: `YahooHistory` (`yfinance` with the `.KL` suffix; coverage and reliability to confirm, T8) and `SnapshotHistory` (daily closes derived from stored `underlying_bid` snapshots).
- Realized volatility needs at least 11 and 31 daily closes for the 10 and 30 day measures; otherwise the result is `unknown`.

### Replay and sample data

- Replay mode needs no source access: every data endpoint accepts a `snapshot_id`.
- `scripts/make_fixtures.py` generates a **synthetic** snapshot set (several underlyings, calls and puts, varied expiries, deliberate edge cases such as crossed quotes and missing bids) from the quant engine. CI and the public fallback use it. It MUST NOT contain real source data.
- If no real snapshots exist, the app loads the synthetic set and the badge says Sample data.

## 8. Quant Engine Implementation

The engine is a package of pure functions with frozen dataclasses (or Pydantic models with `frozen=True`) for inputs and outputs. It has no I/O, no clock access (the `as_of` date is a parameter), and no random numbers. The formulas are defined in the Functional Specification, Section 4; this section covers implementation.

### Module responsibilities

| Module | Functions |
| --- | --- |
| `bs.py` | `bs_price(kind, S, K, r, T, sigma)`, `bs_greeks(...)` returning delta, gamma, vega per point and theta per day; `intrinsic(kind, S, K)`; bounds for no-arbitrage checks |
| `iv.py` | `implied_vol(kind, S, K, r, T, price_per_share)`; `iv_by_basis(row, S, r, T, n)` returning IV for last, size-weighted mid, plain mid, bid and ask, plus the spread of IV across bases |
| `metrics.py` | `compute_metrics(row, r, as_of, ratio_convention)` returning `WarrantMetrics`; mid, size-weighted mid, spread, round-trip cost, gearing, effective gearing, premium, breakeven, required move |
| `scenario.py` | `scenario(row, m, d, dv, r, as_of)`, `curve(...)`, `breakeven_move(...)`, presets |
| `attribution.py` | `attribute(from_row, to_row, r)` sequential decomposition |
| `vol.py` | `realized_vol(closes, window)` |
| `flags.py` | `evaluate_flags(metrics, presets, row, history, config)` returning flags and the not-evaluated list |
| `ratio.py` | `choose_ratio_convention(rows)` implementing the comparison test |

### IV price bases

| Basis | Price used | Notes |
| --- | --- | --- |
| last | Last traded price | Only if present, from the current trading day, and inside a sanity band; otherwise unknown or stale. Not available in the fields read so far (T6) |
| size-weighted mid | (bid x ask size + ask x bid size) / (bid size + ask size) | Falls back to plain mid when either size is missing or zero, and the output states the fallback |
| mid | (bid + ask) / 2 | Used for the scenario baseline `sigma0` |
| bid, ask | Quotes | Low and high ends of the range |

The headline basis defaults to size-weighted mid and is a parameter of the API. The engine returns all bases so the UI toggle is a display switch, with no recalculation.

**Size-weighted mid and its meaning.** The formula weights each quote by the opposite side's size, so a thick bid pulls the value toward the ask. The Functional Specification describes it as size-weighted; document it in the UI tooltip as a quote-based estimate, not a traded price. The units of the sizes (thousands) cancel out, but both must use the same unit.

### Numerics

- Normal CDF through `scipy.special.ndtr` or `math.erf`; vectorized helpers for lists.
- IV solver: bracket `[1e-4, 5.0]`, Brent's method (`scipy.optimize.brentq`) with `xtol=1e-8`. Before solving, check that the target price lies strictly between the lower and upper bounds (for a call, `max(S - K*exp(-rT), 0) * n` and `S * n`; mirrored for puts). Return `None` with a reason code otherwise.
- Reason codes: `no_quote`, `non_positive_price`, `below_intrinsic`, `above_upper_bound`, `expired`, `solver_failed`.
- Very small `T` (under about one calendar hour): treat as expired for forward-looking metrics.
- All results are checked with `math.isfinite`; non-finite becomes `None` with `non_finite`.
- Floating point is `float64`. Prices are not rounded inside the engine; rounding happens in `tools/evidence.py` display formatting.

### Display formatting (single source of truth)

`tools/evidence.py` formats every number once, on the server: currency with the precision of the source quote, percentages with one decimal, multiples with one decimal, IV in points with one decimal. Both the raw value and the display string travel to the client and to the model. The verifier matches the display strings (Section 11); the UI renders the same strings or formats from raw values with the same rules, tested against shared fixtures.

### Performance

- Target: the full warrant list for one stock (a few hundred rows) with five IV bases per row in well under a second on one CPU core. Measure in M1.
- If per-row `brentq` is too slow: first vectorize with a Newton iteration on vega with a bisection safeguard; second cache metrics by `(snapshot_id, code, r, ratio_convention)`.
- Run list computations in a bounded thread pool so the event loop is not blocked.
- An in-process LRU cache holds `WarrantMetrics` and card results keyed by snapshot and parameters; snapshots are immutable so entries never go stale.

### Flags engine

- Thresholds are loaded from `config/flags.yaml` (the table in the functional spec is the default file).
- Output is a list of `{code, severity, value, threshold, text}` plus `not_evaluated` entries with a reason, such as no price history.
- The IV-range flag compares the maximum and minimum IV across bases.
- The last-trade flag fires when the last price is outside the bid-ask range or not from the current trading day.

### Ratio convention test

`choose_ratio_convention(rows)` computes effective gearing for both readings across all valid rows, compares to the issuer's value, and returns the reading with the lower median absolute relative error plus both errors. The collector runs it on the first snapshot and logs the result; a regression test fails if the winning convention changes on the fixture set.

### Required tests

- Golden values from the functional spec (call, put, delta, gamma, vega, theta); put-call parity; IV round trip across a grid; monotonicity.
- Scenario identity: zero move, zero days and zero shift gives bid / ask - 1.
- Attribution parts sum to the total within `1e-9`.
- Size-weighted mid: symmetric sizes give plain mid; a larger bid size moves the value toward the ask; missing size falls back with the label.
- IV bases: each basis returns the expected IV for a price generated at a known volatility.
- Property tests with Hypothesis over valid ranges: no exceptions, no NaN, finite or `None`.
- Benchmarks (not gating): list computation time recorded in CI output.

## 9. API Layer

The endpoint list and entity fields are defined in the Functional Specification, Section 9. This section fixes how they are implemented.

### Application structure

- `api/app.py` builds the FastAPI app with a lifespan that creates the SQLite engine, HTTP clients, Tavily gateway, model factories, the ADK runner and background tasks (scheduler if enabled, session janitor). Shutdown closes them.
- Routers: `meta`, `data` (underlyings, warrants, card, scenario, compare, stock, news, explain-move, snapshots), `chat`, `report`.
- Pydantic models are the single source of truth. FastAPI generates the OpenAPI document; the web build generates TypeScript types from it with `openapi-typescript` and calls the API through `openapi-fetch`. A CI step fails if the generated types are out of date.
- The built SPA is served from `web/dist` with a fallback to `index.html` for client routes. Unknown `/api/*` paths return a JSON 404, never HTML.

### Request handling

| Concern | Specification |
| --- | --- |
| Request id | Middleware adds an id to every request and log line and returns it in a response header |
| Validation | Pydantic field constraints with the ranges in the functional spec; failures return `422` mapped to the error shape below |
| Error shape | `{error: {code, message, field?, retry_after?}}`; never stack traces; codes are stable strings such as `invalid_input`, `not_found`, `rate_limited`, `budget_exhausted`, `source_unavailable`, `model_unavailable` |
| Rate limiting | Token bucket per hashed client key (hash of IP plus a daily-rotating salt) held in memory; defaults 30 chat requests per hour and a higher limit for data endpoints; client IP taken from a forwarded header only if configured as trusted |
| Budget guard | Reads the `budgets` table for today (Malaysia date); denies model-backed requests with `budget_exhausted` when the cap is reached and serves stored answers where available |
| CORS | Disabled when the SPA is served by the same origin; an allow-list for local development |
| Caching | Snapshot-based GET responses carry an `ETag` derived from `(snapshot_id, params)` and `Cache-Control: no-cache` so the client revalidates cheaply |
| Size limits | Chat message at most 1,000 characters; JSON body size limit enforced by the server |

### Chat endpoint and SSE protocol

`POST /api/chat` returns `text/event-stream`. Browsers cannot use `EventSource` with POST, so the client uses `@microsoft/fetch-event-source`.

| Event | Data (JSON) |
| --- | --- |
| `turn_started` | `{turn_id}` |
| `status` | `{step, text}` where text comes from a static map |
| `tool_call` | `{name, args}` with arguments redacted to the allowed fields |
| `evidence` | `{evidence_id, kind, source, as_of, summary}` |
| `card` | `{WarrantCard}` or `{StockSummary}` for the panel |
| `token` | `{text}` (verified text only) |
| `verifier` | `{passed, retried, removed_sentences}` |
| `usage` | `{model, tier, in_tokens, out_tokens, latency_ms, cost_usd}` |
| `done` | `{turn_id}` |
| `error` | `{code, message, recoverable}` |

Transport details:

- Response headers `Cache-Control: no-cache` and `X-Accel-Buffering: no`; a comment heartbeat every 15 seconds so proxies do not close idle connections.
- If the client disconnects, the server cancels the running turn (cancel the ADK task) and records the partial usage.
- Event ids are monotonically increasing per turn. Mid-turn resume is not supported; the client shows a retry control instead.
- Server-side flag `WX_STREAM_DRAFT` (default false) sends draft text early and a final replacement event; it exists for latency experiments only because it breaks the rule that unverified figures are never shown.

### Turn runner (pseudo-code)

```python
async def run_turn(req, deps) -> AsyncIterator[SseEvent]:
    yield started(req)
    deps.guard.check(req)                                   # rate limit, budget
    if intent.is_pure_advice(req.message):                  # rules, then Nano if ambiguous
        yield from refuse_with_alternatives(req)
        return
    session = deps.sessions.get_or_create(req.session_id, state=req.state())
    async with asyncio.timeout(deps.settings.turn_timeout_s):
        draft = None
        async for ev in deps.runner.run_async(user_id=session.user, session_id=session.id, new_message=req.content):
            for sse in adapt(ev):                            # tool_call, status, evidence, card
                yield sse
            if ev.is_final_response():
                draft = extract_text(ev)
        result = guardrails.verify_and_lint(draft, deps.evidence_for(req.turn_id))
        if not result.passed:
            draft = await deps.regenerate_once(session, result)       # corrective message, same session
            result = guardrails.verify_and_lint(draft, deps.evidence_for(req.turn_id))
            if not result.passed:
                draft = guardrails.strip_and_note(draft, result)
    for chunk in chunk_text(draft):                          # about 30 characters, short delay
        yield token(chunk)
    yield verifier(result); yield usage(deps.usage_for(req.turn_id)); yield done(req)
```

On `TimeoutError`, return the grounded text produced so far (if any) with a partial notice. On any other exception, emit `error` and log with the request id.

### Non-chat endpoints

- `GET /api/warrants` accepts an `iv_basis` parameter (last, size\_weighted\_mid, mid, bid, ask) that only changes which IV is the headline; all bases are always returned.
- `GET /api/stock/{ticker}` returns the summary plus the full list of warrants with metrics (paged by `limit` and `cursor`, default page large enough for one stock).
- `POST /api/scenario` and `GET /api/warrants/{code}` call the same functions the chat tools use (functional rule: identical results).
- `POST /api/compare` rejects mixed underlyings with the documented message.
- `GET /api/meta` includes resolved model IDs, tier health, source health, mode, as-of time, staleness and the version string.
- Admin routes (usage and cost totals, cache clear) are mounted only if `WX_ADMIN_TOKEN` is set and require it as a bearer token.

### Tests

- Contract tests against the OpenAPI document for every route using the synthetic fixtures.
- SSE tests with `FakeLlm`: event order, heartbeat, cancel on disconnect, error mapping, verified-before-stream behavior.
- Rate limit and budget tests with a fake clock.

## 10. Frontend: Vite, React and UX

A single-page app built with Vite. It only displays what the API returns: no pricing math, no metric recomputation. Screens and requirements are defined in the Functional Specification, Section 8; this section fixes the technology and the experience design.

### Stack

| Concern | Choice | Reason |
| --- | --- | --- |
| Build | Vite with the React plugin, TypeScript `strict` | Fast dev server and builds |
| UI | React with function components and hooks |  |
| Styling | Tailwind CSS with CSS-variable design tokens | Fast, consistent, light and dark themes |
| Primitives | Radix UI (tabs, dialog, tooltip, popover, switch, slider) | Accessible behavior out of the box |
| Server state | TanStack Query | Caching, cancelation, retries keyed by `snapshot_id` |
| UI state | Zustand | Small store for chat, active warrant and selections |
| Tables | TanStack Table with TanStack Virtual | Sorting, filtering and virtual rows for stocks with many warrants |
| Charts | Recharts | Enough for P&L curves; custom SVG only if needed |
| Streaming | `@microsoft/fetch-event-source` | SSE over POST with abort support |
| API types | `openapi-typescript` and `openapi-fetch` | Types generated from the backend OpenAPI document |
| Markdown | `react-markdown` with `remark-gfm` and `rehype-sanitize`; custom renderer for `[E#]` chips | Safe rendering of answers |
| Tests | Vitest, Testing Library, MSW, Playwright, axe-core | Unit, component, mocked SSE, end-to-end, accessibility |
| Lint and format | ESLint and Prettier |  |

### Vite configuration

```ts
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } }, // SSE passes through
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: { output: { manualChunks: { charts: ['recharts'] } } },
  },
});
```

- The API base path is relative (`/api`), so the same build runs behind the FastAPI static mount. `VITE_API_BASE` overrides it for separate deployments.
- Target initial JavaScript under about 250 KB gzipped, with the chart library loaded as a separate chunk. Treat this as a target to measure, not a verified number.

### Folder structure

```text
web/src/
  api/            # generated types, client, query keys, sse.ts
  state/          # useChatStore, useSessionStore, useSelectionStore
  features/
    chat/         # ChatPanel, MessageList, AssistantMessage, CitationChip, ToolTrace, Composer, SamplePrompts
    stock/        # StockTab, WarrantTable, StockSummaryBar, IvBasisToggle, FilterBar
    card/         # CardTab, MetricPair, HoldingCostBar, FlagChip, FlagDrawer
    scenario/     # ScenarioTab, ScenarioSliders, PnlChart, AssumptionsNote
    compare/      # CompareTab
    sources/      # SourcesTab, NewsItemCard, EvidenceRecord
    health/       # DataHealthTab
    shell/        # AppShell, Header, DataBadge, SnapshotPicker, StatusBanner, DisclaimerBar, Footer
  ui/             # Button, Tabs, Sheet, Tooltip, Skeleton, EmptyState (thin wrappers on Radix + Tailwind)
  lib/            # format.ts (numbers, dates), copy.ts (all user-facing strings), glossary.ts
  styles/         # tokens.css, globals.css
  main.tsx  App.tsx
```

### State and data flow

- **Server state** (warrant lists, cards, scenarios, news, meta) goes through TanStack Query. Query keys include `snapshot_id` and parameters, so switching snapshot refetches everything consistently.
- **Chat state** lives in Zustand: messages with parts (text, status, tool trace, evidence refs), `evidenceById`, active warrant code, active tab, session id. The session id is created once and kept in `sessionStorage`.
- **Scenario requests** use an `AbortController`; a new slider value cancels the previous request. The previous result stays visible while the new one loads (functional rule). Debounce 150 ms.
- **Formatting** goes through `lib/format.ts`, which mirrors the server rules (Section 8) and is tested against shared fixtures. When the server sends a display string, the UI uses it as is.

```ts
// api/sse.ts (sketch)
import { fetchEventSource } from '@microsoft/fetch-event-source';

export function streamChat(body: ChatRequest, handlers: Handlers, signal: AbortSignal) {
  return fetchEventSource('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
    openWhenHidden: true,
    onmessage(ev) { handlers[ev.event]?.(JSON.parse(ev.data)); },
    onerror(err) { handlers.error?.({ code: 'connection_lost', message: String(err), recoverable: true }); throw err; },
  });
}
```

On `onerror` the handler rethrows so the library does not retry automatically; the UI shows a retry control instead (no mid-turn resume).

### Layout and responsive behavior

| Width | Layout |
| --- | --- |
| 1280 px and wider | Two panes: chat about 40 percent, evidence panel about 60 percent |
| 768 to 1279 px | Two panes, evidence panel can collapse to a narrow rail |
| Under 768 px | Chat full screen; evidence panel opens as a bottom sheet from a floating button or when an answer produces a card; sheet snaps to half and full height |

### Design system

**Principles:** calm, data-first, honest. Numbers are the stars; decoration is minimal; nothing looks like a trading signal.

| Token group | Specification |
| --- | --- |
| Typography | Inter (or system UI) for text; a monospace face for warrant codes and evidence ids; tabular numerals on every number column; base size 15 px on desktop, 16 px on mobile |
| Spacing | 4 px scale; table row height 40 px compact, 48 px comfortable; chat bubble padding 12 to 16 px |
| Color roles | Surface, surface-raised, border, text, text-muted, accent, plus status roles info, warn, high, ok. Each status color is always paired with an icon and a text label |
| Themes | Light and dark through CSS variables on `:root`, driven by `prefers-color-scheme` with a manual toggle stored in `sessionStorage` |
| Contrast | WCAG AA or better for text and for status chips in both themes |
| Motion | 150 to 200 ms transitions; all non-essential animation disabled under `prefers-reduced-motion` |
| Iconography | One outline icon set; icons never carry meaning alone |

Semantic copy rules (kept in `lib/copy.ts`): plain language; never use recommendation words (buy, sell, best, top pick, opportunity, avoid); describe conditions and costs; label unknown values with a reason; a glossary tooltip for delta, theta, IV, gearing, premium, breakeven and spread.

### Key components and behavior

**Header and data badge.** Product name; badge reading Live or Replay or Sample data with the Malaysia-time as-of and a stale marker; snapshot picker (a popover list of stored snapshots with date and time); a link that opens the disclaimer.

**Chat panel.** Message list with a visible status line per tool step; assistant messages rendered with sanitized Markdown; `[E#]` rendered as small chips that, on click or Enter, switch the evidence panel to Sources and highlight the record; a collapsible Data steps list; a composer with a character counter at 1,000; a row of sample prompts on first load; a Deep risk report button on warrant cards.

**Stock tab (the all-warrants view).** When a stock is resolved, this tab opens automatically:

- A summary bar: price and as-of, counts of calls and puts, issuers, expiry range, median spread cost, median decay, flag counts, realized volatility if available.
- The warrant table with filters (call or put, issuer, days to expiry, moneyness, flag) and a toggle to group calls and puts under sticky group headers.
- Default columns: code, issuer, type, expiry and days left, strike, moneyness and distance, bid, ask, bid and ask size, last price and time, spread cost, headline IV, issuer IV, delta, effective gearing, theta per day, breakeven move, flat decay, flags. Optional columns come from a column picker.
- An **IV basis** segmented control (last, size-weighted mid, mid, bid and ask range) that changes the headline IV column only; the row expander shows all bases and the issuer value with the gap.
- Sticky header and sticky first column, virtualized rows, stable sorting, right-aligned tabular numbers, `—` with a tooltip for unknown values, flag chips with icon and text.
- Selecting a row opens its card; a checkbox on up to 3 rows enables Compare.
- Marks the highest and lowest value in a column on request, but never shows rank numbers or best labels.

**Card tab.** A two-column metric grid (Issuer says, We recompute) with difference markers; flag chips that open a drawer showing the measured value, threshold and a one-sentence explanation; a holding-cost bar chart for spread cost, flat decay and IV crush; a holding-days stepper.

**Scenario tab.** Three sliders with numeric inputs (move, days, volatility shift); a line chart with three horizons distinguished by color and dash pattern, a marker at the current setting and an annotation at the breakeven move; the three assumptions printed beneath; reset button.

**Sources tab.** News items as cards (title, domain, date or undated, event type, up to 3 facts, unconfirmed label or corroboration count, link opens in a new tab with `rel` set to `noopener noreferrer`); data records and calculations used in the answer, each with its evidence id and time.

**Data health tab.** Mode, as-of, staleness, last successful and failed collection, row counts, quality check results, model tier used per step, and any items dropped by the injection filter.

### Screen flows

1. **First visit.** Explanation, disclaimer, sample prompts, badge shows mode. Clicking a sample prompt sends it and opens the matching panel tab as results arrive.
2. **Enter a stock.** The status line shows steps; the Stock tab fills with the full warrant list; the chat gives a short grounded summary with reference chips.
3. **Drill down.** Row selection opens the Card tab; the holding-days stepper updates figures; Scenario tab starts from the same warrant and holding period.
4. **Ask a question.** Any chat answer about a warrant keeps the Card tab in sync.
5. **Deep report.** The button shows step progress; the report appears as an expandable panel with Copy and export.
6. **Degraded states.** A banner above the panels states the cause and the fallback in use; controls that cannot work are disabled with a reason.

### Accessibility

- Tabs follow the WAI-ARIA tabs pattern; the table uses real table semantics with column headers and sort state announced; the chip list is a labeled group.
- Streaming status text sits in a polite live region; the verified answer is announced once when complete.
- Focus management: after sending, focus stays in the composer; opening the sheet moves focus into it; closing returns focus to its trigger.
- Keyboard: `/` focuses the composer, `Esc` closes sheets and popovers, arrow keys move within tables and sliders.
- Targets at least 44 px on touch screens; visible focus rings; no information by color alone.

### Front-end tests

| Layer | Coverage |
| --- | --- |
| Unit | `format.ts` against shared fixtures, store reducers, SSE event handlers |
| Component | Table sorting and filtering, IV basis toggle, flag chips, scenario sliders with MSW mock, citation chips |
| Accessibility | axe-core on each tab and in both themes |
| End-to-end | Playwright in replay mode with the fake model: first load, stock entry, drill down, scenario change, advice refusal, source-down banner, mobile viewport |
| Visual (optional) | Screenshot checks for the table and chart |

## 11. Guardrails: Grounding, Advice Boundary and Injection Defense

Three layers protect the product's core promises (numbers from code, no advice, web text is data). Layer 1 lives in the ADK plugin (Section 4), layer 2 in the API layer after the agent finishes, layer 3 in the news pipeline (Section 6).

### Order of checks in a turn

1. **Input:** length and character checks; rate limit; budget.
2. **Advice-intent pre-check:** deterministic rules (English and Malay patterns), then a Nano call only when the rules are ambiguous. A pure advice request gets the templated refusal and offers; the agent is not called.
3. **During the loop:** the plugin validates tool arguments, caps tool calls, wraps tool results as Evidence and builds the turn allowlist.
4. **Output:** the grounding verifier, then the advice linter, then the regenerate-once rule, then strip-and-note.
5. **After streaming:** persist evidence and metrics for the grounding pass-rate report.

### Grounding verifier (`guardrails/verifier.py`)

Because tools return server-formatted `display` strings and the model is told to copy them (decision D4), the verifier works mainly by exact string match.

**Allowlist per turn**

- Every `display` string in this turn's evidence, and every raw number rendered with the server's formatting rules.
- Numbers the user typed in the conversation (including percentages and days).
- Dates and times that appear in evidence, in any of the formats the UI shows.
- Evidence ids such as `E3` and list markers.

**Extraction.** Tokenize the answer with a number regex that covers thousands separators, decimals, signs, `%`, `x` multiples, `RM` prefixes, ranges (`3 to 5`), and unit suffixes (days, points, ticks). Normalize each token to a canonical string and a `Decimal` value.

**Matching.** A token passes if its canonical string is in the allowlist. If not, it may still pass a numeric check: equal to an allowlisted value after rounding to the number of decimals the token shows, within half a unit of its last digit. Approximations such as about 5 percent pass only when they round-match an evidence value. Counts (for example the number of warrants) must also come from evidence.

**Outcome.**

| Result | Action |
| --- | --- |
| All tokens pass | Continue to the linter |
| Some fail, first attempt | One corrective message in the same ADK session, listing the failing tokens and asking the model to use only evidence display strings; re-run |
| Some fail again | Split into sentences; delete each sentence containing a failing token; append the omission note; if nothing is left, return a templated summary built from evidence display strings |

Each attempt is logged with counts so the evaluation can report first-pass, after-retry and stripped rates.

```python
@dataclass(frozen=True)
class VerifyResult:
    passed: bool
    failing_tokens: list[str]
    failing_sentences: list[int]

def verify(answer: str, allow: Allowlist) -> VerifyResult: ...
def strip_and_note(answer: str, result: VerifyResult) -> str: ...
```

**Known limits to test and tune:** years and phone-like numbers in company names, ordinal words, numbers inside quoted news facts (these come from evidence and are allowlisted as stated numbers), and Malay number formats.

### Advice linter (`guardrails/linter.py`)

- Patterns live in `config/linter_patterns.yaml` and are applied after Unicode normalization and case folding.
- English patterns include strong buy, speculative buy, you should buy or sell, I recommend buying or selling, target price, stop-loss at a level, guaranteed, can't lose and sure profit.
- Malay patterns cover equivalents (for example buy, sell, target price and stop-loss terms), maintained in the same file.
- A numeric-advice check flags a price or percentage presented as an entry, exit, target or stop.
- On a match: regenerate once with an explicit instruction; on a second match return the fixed safe template.
- The linter also runs on Deep Risk Report text, on templated fallbacks, and on the Discord adapter output.

### Advice-intent pre-check (`guardrails/intent.py`)

- Rules detect questions asking whether to buy, sell or hold, for targets or stops, or for predictions of future price, in English and Malay, including pressure phrasing.
- A request that mixes advice with a legitimate question is passed to the agent with an extra instruction line; the linter protects the output.
- The templated refusal states the boundary in one sentence and offers the cost view, breakeven and scenario for the named warrant or stock, filled with display strings from a quick card lookup when a warrant is named.

### Prompt-injection defense

| Control | Where |
| --- | --- |
| Raw web text never reaches Super or Ultra; only validated `NewsItem` objects do | Section 6 |
| Untrusted wrapper tags around any web-derived text passed to a model, with a rule in the system prompt to treat it as data | Prompts |
| Strict extraction schema with short fields and enumerated values | Nano structuring |
| Pattern filter removes facts that contain instructions, system-prompt mentions or URLs | Section 6 |
| Tools accept identifiers and numbers only; no tool takes a URL or code from the model | Plugin before-tool hook |
| Per-turn tool-call cap and per-session model-call cap | Plugin |
| Reasoning content and system text are never echoed to the user | Plugin after-model hook |
| Requests to reveal instructions or ignore rules get the standard decline | Intent rules, system prompt |

### Disclaimer and templates

- All user-visible fixed strings (disclaimer, refusal, omission note, degraded-state messages) are in one module, `guardrails/templates.py`, in English and Malay, and are covered by tests.
- The disclaimer line is appended by code, not by the model, so it cannot be omitted.

### Tests

- Verifier unit tests for each number format, rounding edge, and a corpus of passing and failing answers.
- Linter tests with positive and negative examples in English and Malay.
- Red-team suite: direct advice requests, pressure variants, mixed requests, canary-token injection pages, attempts to extract the system prompt, prompts in Malay.
- Metric: zero advice leaks and zero followed injections across the suite; the first-pass grounding rate is reported, not hidden.

## 12. Observability, Cost Tracking, Configuration and Secrets

### Logging

- `structlog` writes JSON lines to stdout. Every line carries `ts`, `level`, `request_id`, and when relevant `turn_id`, `session_hash`, `tier`, `tool`, `latency_ms`.
- Never log API keys, raw IP addresses, full user messages beyond a configurable truncation (default: first 80 characters, off in production if the owner prefers), reasoning text, or raw source rows.
- Client keys are a hash of the IP plus a daily-rotating salt; session hashes are a hash of the session id.

### Metrics that must be computable from stored data

| Metric | Source | Used for |
| --- | --- | --- |
| Cost and tokens per call, per tier, per day | `llm_calls` | Cost chart, budget guard, ablation |
| p50 and p95 latency per tier and per tool | `llm_calls` and tool timing logs | Latency table, tier decisions |
| Grounding first-pass, after-retry and stripped rates | Turn records written by the API layer | Evaluation results |
| Advice-linter hits and refusals | Turn records | Red-team report |
| Tavily credits per day and per turn | `budgets` and gateway counters | Tavily budget |
| Collector success rate, row counts, quality flags | `snapshots` | Data health |
| Fallback and circuit-breaker events | Logs | Reliability notes for feedback |

A script, `scripts/cost_report.py`, prints totals per day and per tier and exports the table used in the README. The published cost and latency numbers MUST come from this script.

### Tracing

- Each turn has a span tree: turn, model calls, tool calls, Tavily calls, verifier. A lightweight in-process tracer records durations into the turn record.
- ADK may offer OpenTelemetry integration; evaluate it in T3 and adopt only if it is simple. It is optional.

### Budgets and guards

- Two counters per Malaysia calendar day in `budgets`: LLM spend in USD and Tavily credits. Updates are atomic (single SQL statement with a check).
- Warn at 80 percent of a cap; at 100 percent model-backed requests return the stored-or-templated fallback and the UI shows the banner.
- Per-session caps: at most 3 Deep Risk Reports and a maximum number of model calls per turn.

### Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `WX_MODE` | `live` or `replay` | `replay` |
| `WX_NEBIUS_API_KEY` | Token Factory key | required in live |
| `WX_NEBIUS_BASE_URL` | Base URL | `https://api.tokenfactory.nebius.com/v1/` |
| `WX_MODEL_NANO`, `WX_MODEL_SUPER`, `WX_MODEL_ULTRA`, `WX_MODEL_FAST` | Model IDs | from T1; startup check against the model list |
| `WX_REASONING_EFFORT_NANO`, `_SUPER`, `_ULTRA` | Reasoning effort per tier | low, low, medium (confirm support, T1) |
| `WX_LLM_STUB` | Use the fake model (tests and offline demo) | `false` |
| `WX_TAVILY_API_KEY` | Tavily key | required for news |
| `WX_TAVILY_DAILY_CREDITS` | Daily Tavily cap | 200 |
| `WX_MIBB_BASE_URL` | Source endpoint base | from T6 |
| `WX_SOURCE_ENABLED` | Collector kill-switch | `true` |
| `WX_DB_URL` | Database location | `sqlite+aiosqlite:///data/warrantx.db` |
| `WX_RISK_FREE_RATE` | Annual rate | `0.03`, to be confirmed |
| `WX_LLM_DAILY_USD_CAP` | Daily model spend cap | `10` |
| `WX_RATE_LIMIT_CHAT_PER_HOUR` | Per-client chat limit | `30` |
| `WX_TURN_TIMEOUT_S` | Turn limit | `60` |
| `WX_STREAM_DRAFT` | Draft streaming experiment | `false` |
| `WX_FEATURE_CHATTER`, `WX_TAVILY_RESEARCH`, `WX_TAVILY_CRAWL` | Optional features | `false` |
| `WX_ADMIN_TOKEN` | Enables admin routes | unset |
| `WX_LOG_LEVEL` | Log level | `INFO` |

### Secrets

- Secrets exist only as environment variables supplied by the hosting platform or a local `.env` that is git-ignored. `.env.example` lists names without values.
- Keys are never sent to the browser, never baked into images, never printed. The web build contains no secrets.
- CI runs a secret scan on every push and a full-history scan before the repository is made public.
- Rotate any key that appears in a log, an issue, a screenshot or a video.

### Operational runbook (short)

| Situation | Action |
| --- | --- |
| Source blocks or terms change | Set `WX_SOURCE_ENABLED=false`; app serves stored snapshots; note in Data health |
| Model tier failing | Check `/api/meta`; circuit breaker already skips; adjust model ID or tier mapping |
| Spend rising fast | Lower `WX_LLM_DAILY_USD_CAP`; inspect `scripts/cost_report.py`; check for abuse in rate-limit logs |
| Tavily credits low | Lower per-turn extract count; rely on cache; disable optional features |
| Bad snapshot | Mark it `suspect` in `quality_json`; the previous good snapshot stays current |

## 13. Testing, CI and Deployment

### Test strategy

| Layer | Tooling | What it proves | Network |
| --- | --- | --- | --- |
| Unit: quant and data | pytest, hypothesis | Correct math, parsing, normalization, edge cases | none |
| Unit: guardrails | pytest | Verifier and linter behavior on corpora (English and Malay) | none |
| Integration: agent flow | pytest-asyncio with `FakeLlm` | ADK loop, callbacks, event mapping, evidence, regenerate-once, strip-and-note | none |
| Integration: external clients | `respx` fixtures | Source client and Tavily gateway, including empty and error cases | none |
| Contract | OpenAPI schema validation | Every route matches the published schema | none |
| End-to-end | Playwright, replay mode, `WX_LLM_STUB=true` | Real browser, real API, deterministic model | none |
| Live smoke | pytest marker `live`, manual | The T1 model matrix, one Tavily call, one source capture | yes, keys needed |
| Agent eval | `warrantx.eval.agent` | 30 prompts with deterministic assertions on real models | yes |
| Ablation | `warrantx.eval.ablation` | Cost and latency for all-Ultra, all-Super and tiered | yes |
| Model fit | `warrantx.eval.model_fit` | Scenario predictions against stored snapshot pairs | none |

`FakeLlm` is a `BaseLlm` subclass that returns scripted function calls and texts keyed by scenario name. It lets CI exercise the whole ADK path, including the plugin hooks, without a key.

### Continuous integration (GitHub Actions)

| Job | Steps |
| --- | --- |
| `backend` | `uv sync --frozen`, `ruff check`, `ruff format --check`, `mypy` (strict on `quant/`), `pytest` excluding `live` |
| `web` | `npm ci`, ESLint, type check, Vitest, `vite build`, regenerate API types and fail on diff |
| `e2e` | Build image or run both servers in replay mode with the stub model; Playwright tests including mobile viewport and axe checks |
| `security` | `gitleaks` (or equivalent) on the diff, `pip-audit`, `npm audit` (report, with manual review of findings) |
| `release` (manual) | Build and tag the image; run the smoke script against the deployed endpoint |

Branch protection: a merge requires the `backend`, `web` and `e2e` jobs to pass.

### Container image

- Multi-stage Dockerfile: stage 1 builds `web/dist`; stage 2 installs the Python app from the lockfile and copies the built assets; the final image runs as a non-root user.
- Command: `uvicorn warrantx.api.app:app --host 0.0.0.0 --port 8000`; the same image runs the collector and evals with a different command.
- A health check calls `GET /api/health`. The image contains no secrets and no real snapshot data; a synthetic sample database is baked in for fallback.
- Local development: `docker compose up` with a volume for the SQLite file and `.env`; `make dev` runs backend and Vite dev server together.

### Deployment on Nebius (to be confirmed, T7)

Nebius-specific commands, limits and features were not verified. The agent MUST read the current Nebius docs for Serverless Endpoints and Jobs and record exact commands in `docs/DEPLOY.md`. The intended shape:

| Piece | Intended setup |
| --- | --- |
| Registry | Push the image to a registry the platform can pull from (confirm which) |
| Endpoint | One public HTTP endpoint, port 8000, health path `/api/health`, minimum and maximum replicas both 1 (in-memory sessions and scheduler), secrets as environment variables |
| Storage | A persistent volume or object storage for the SQLite file, if the platform supports it; otherwise a baked sample database and a collector inside the container |
| Jobs | Collector (if separate) and eval runs; results copied to storage and to the repo |
| Model access | Token Factory from the same platform account; confirm network access and any rate limits |
| Domain and TLS | Platform-provided URL is sufficient for the submission |

**Always-on requirement.** The in-process scheduler and in-memory sessions need one instance that does not scale to zero. If the platform cannot guarantee that, move collection to a Job with shared storage and accept that sessions may reset on cold start.

### Release checklist

- [ ] CI green on the release commit; `live` smoke tests run once against the target models.
- [ ] Image built from the tagged commit; digest recorded.
- [ ] Environment variables set; `/api/meta` shows the expected mode, models and tier health.
- [ ] Smoke script passes: `/api/health`, `/api/meta`, a stock list, a card, a scenario, a chat turn with a sample prompt, an advice refusal.
- [ ] Rate limits and budget cap confirmed on the deployed endpoint.
- [ ] Public URL opened from a phone and a clean browser profile.
- [ ] Previous image tag kept for rollback.

### Rollback and incident handling

- Rollback is redeploying the previous image tag; snapshot data is unaffected because it is append-only.
- If an upstream (source, Nebius, Tavily) fails during the demo period, the app degrades as specified in the functional spec; the operator checks `/api/meta` and the Data health tab first.
- Keep a short post-incident note in `docs/FEEDBACK.md`, since platform friction is also useful submission feedback.

## 14. Integration Risks and Verification Tasks

Each task below closes one or more *VERIFY* items. Record the date, method and result in `docs/VERIFIED.md`. Tasks T1 to T3 and T6 are spikes for the first two days of the build and decide whether the plan holds.

### Verification tasks

| ID | Task | Closes | Pass condition | If it fails |
| --- | --- | --- | --- | --- |
| T1 | Run the capability matrix (Section 5) on Nano, Super, Ultra and, optionally, Lightning through Token Factory with the OpenAI SDK | Tool calling, parallel calls, forced tool choice, JSON schema, reasoning effort, token use | Super (or Lightning) returns valid tool calls reliably; Nano returns valid JSON | Choose another tier for the failing role; use prompt-based JSON; drop reasoning effort control; document in feedback |
| T2 | End-to-end ADK loop with `LiteLlm` against Token Factory: two tools, tool result fed back, final answer | Adapter compatibility, `openai/` plus two-slash model IDs, kwarg pass-through (`timeout`, `num_retries`, extra body) | The loop completes with correct tool arguments on the chosen Super tier | Write a `BaseLlm` subclass over the OpenAI SDK; if still blocked, use the plain-loop fallback (decision D1) |
| T3 | ADK behaviors: non-streaming text with function-call events, `output_schema` with and without tools, `temp:` state scope, plugin hooks reaching sub-agents, tool default parameters, `BaseLlm` signature, `LlmAgent` config keywords, optional tracing | Section 4 VERIFY items | Each behavior observed in a small script against the installed version | Adjust the design (for example move state to a context variable, avoid defaults, drop `output_schema`) and record it |
| T4 | Read `/v1/models`; confirm IDs, context sizes (resolve the Ultra 256K versus 1,024K conflict), rate limits and current prices | Model catalog, `prices.yaml`, concurrency limit | Configured IDs exist; limits and prices recorded with date | Change IDs; set the semaphore lower |
| T5 | Tavily checks: results and `published_date` for each configured Malaysian domain, extraction on exchange announcement pages, credits per call, rate limits | Section 6 VERIFY items | At least three of the configured sources return dated, relevant items for common tickers | Change the domain list; rely on snippets; adjust the single-source label policy |
| T6 | Source checks: capture a real response; confirm base URL, field names and units, whether a last traded price exists, ratio direction, exercise style, meaning of theta and sensitivity, trading hours, holidays, terms of use and permission | Section 7, all functional open items about data | Real fixture captured; data dictionary written; terms allow the planned use | Contact the issuer's team; use a curated set with manually entered terms; keep replay-only mode |
| T7 | Nebius Serverless: always-on instance, scheduling, persistent storage or object storage, registry, secrets, public URL | Section 13 | One instance stays up; data persists across restarts or the baked-data fallback is accepted | Collector inside the container; accept session reset on restart |
| T8 | Yahoo Finance `.KL` coverage for the underlyings used | Section 7 history | Daily closes for at least the most active underlyings | Snapshot-derived history only; volatility context unknown for a while |
| T9 | Observe where Nemotron reasoning content appears through LiteLLM and ADK (separate field, think tags, or inside content) | Reasoning stripping rules | Reasoning is removable reliably before verification and display | Add stripping rules for the observed format; reduce reasoning effort |
| T10 | Measure p50 and p95 latency per tier with tools and realistic prompts; decide Super versus Lightning for the chat loop and whether Ultra fits the deep-report timeout | Tier assignment, timeouts | Chat first status under a few seconds and full answer within the turn limit | Use the faster tier for chat; cache deep reports; raise Ultra timeout and show progress |

### Decision gates

| Gate | When | Decision |
| --- | --- | --- |
| A | After T1 and T2 | Keep ADK with `LiteLlm`, switch to a custom `BaseLlm`, or fall back to the plain loop |
| B | After T6 | Collect live data, or run on a curated set and replay data only |
| C | After T10 | Final tier mapping and timeouts, recorded in `docs/DECISIONS.md` |

### Risk register (technical)

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| ADK and `LiteLlm` mishandle Nemotron tool calls or message roles | Medium | High | T2; version pinning; custom `BaseLlm`; plain-loop fallback behind the same tool layer |
| Reasoning models exhaust token budgets or return errors with tools | Medium | High | Generous `max_tokens`, low reasoning effort for tool turns, T1 matrix, strip rules |
| Ultra latency breaks the demo | Medium | Medium | Deep report is optional, asynchronous with progress, cached; fallback to Super |
| Verified-then-stream makes answers feel slow | Medium | Medium | Stream status and evidence early; measure time to first status; consider a faster tier; keep draft streaming as an experiment only |
| Rate limits on Token Factory or Tavily | Medium | Medium | Semaphore, cache, budgets, backoff, stored fallbacks |
| In-memory sessions and scheduler lost on restart or scale-to-zero | Medium | Medium | One always-on instance; collector fallback; sessions are disposable |
| SSE buffered by a proxy | Low | Medium | `X-Accel-Buffering: no`, heartbeat, test on the deployed endpoint early |
| ADK or SDK versions move quickly | Medium | Low to medium | Lockfile, upgrade only with the T2 test green |
| Source endpoint changes or access is restricted | Medium | High | Kill-switch, replay, synthetic data, contact the issuer |
| Grounding verifier too strict or too loose | Medium | Medium | Exact-string design, tune on the eval set, report first-pass rate honestly |
| Browser bundle too heavy for mobile | Low | Low | Chunk charts, virtualize tables, measure |

### Traceability to the Functional Specification

| Functional area | Implemented in |
| --- | --- |
| Source data and ingestion | Section 7 |
| Warrant search, card, flags | Sections 8 and 9, front end in Section 10 |
| Calculation rules, IV bases, cross-check | Section 8 |
| Scenario, compare, explain-a-move | Sections 8 and 9 |
| Stock summary and name matching | Sections 4 and 9 (tools), Section 10 (Stock tab) |
| News context | Section 6 |
| Chat behavior, grounding, advice boundary, Deep Risk Report | Sections 4, 5 and 11 |
| Usage controls and logging | Sections 5, 9 and 12 |
| User interface | Section 10 |
| Errors and degraded modes | Sections 5, 7, 9 and 11 |
| Optional features (Discord, chatter, Malay) | Section 6 (chatter), Section 10 and the Discord note below |

**Discord adapter (optional).** A route on the same app receives signed interaction webhooks, verifies the Ed25519 signature, replies with a deferred response and edits the message when the answer is ready (details to confirm in Discord's developer docs). It calls the same internal functions as the chat route, applies the same verifier and linter, appends the disclaimer in code, and posts nothing unprompted.
