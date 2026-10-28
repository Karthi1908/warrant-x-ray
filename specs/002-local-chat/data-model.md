# Phase 1 Data Model: Local-Only Plain-English Chat

No database tables are added. All new entities are transient (per turn) or configuration.

## Settings (config.py)
| Field | Type | Default | Notes |
|---|---|---|---|
| `chat_enabled` (`WX_CHAT_ENABLED`) | bool | `false` | First layer of the local gate |

## `/api/meta` addition
| Field | Type | Notes |
|---|---|---|
| `chat_enabled` | bool | True only if flag is on **and** the request is loopback; UI uses this to show chat |

## ViewLink (transient, built by `chat/links.py`)
| Field | Type | Rule |
|---|---|---|
| `kind` | `card \| scenario \| compare \| stock \| sources \| health \| news` | Enum |
| `label` | string | Static template text, no digits (e.g. "Open the X-Ray card") |
| `href` | string | Relative deep link, e.g. `/?tab=card&code=532641&days=5`; for `news`, the cited external URL |
| `entity` | `{code?, ticker?, codes?}` | Warrant code(s) or ticker the link targets |
| `evidence_id` | string | The `E#` it derives from |
| `retrieved_at` | ISO datetime \| null | Required for `news` links |

**Validation**: `href` must start with `/?` for in-app kinds; `news` href must be an `http(s)` URL that appears in a `NewsItem`. Codes must exist in the active snapshot.

## ChatDescriptor (transient, built by `chat/describe.py`)
| Field | Type | Rule |
|---|---|---|
| `code`, `ticker`, `option_type` | string | Identifiers only (no figures) |
| `phrases` | list[string] | Qualitative sentences from flags and thresholds, digit-free |
| `mode_phrase` | string | "live", "replay" or "sample" in words |
| `glossary` | list[string] | Plain-English term explanations for the terms asked about |

The model prompt is built **only** from `ChatDescriptor`. The numeric `WarrantCard` never reaches the prompt.

## Intent (transient, from Nano JSON)
```json
{ "intent": "explain_warrant | explain_term | compare | news | scenario | other",
  "code": "string | null", "ticker": "string | null", "term": "string | null" }
```
Invalid or empty output falls back to rules-first detection (existing regex + underlying match).

## NumberCheckResult (verifier)
| Field | Type |
|---|---|
| `passed` | bool |
| `offending_tokens` | list[string] |

## State transitions (one chat turn)
`received -> gate_ok -> intent_pre_check (advice/injection) -> classify -> resolve_entities -> build_descriptor + links -> draft (model or template) -> linter -> no_numbers_check -> (retry once -> strip_and_note -> template) -> stream tokens -> links event -> done`
