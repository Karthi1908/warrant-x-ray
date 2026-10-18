# Warrant X-Ray Verification Register

Per `tech_spec.md` Section 14 and the project constitution, provider-specific facts and unverified parameters MUST NOT be treated as facts until confirmed. This register records the status, date, method, and results for verification spikes T1 through T10.

## Verification Tasks (Spikes T1 – T10)

| ID | Task | Target / Focus | Pass Condition | Fallback if Failed | Status | Date Verified | Results / Notes |
|:---|:---|:---|:---|:---|:---:|:---:|:---|
| **T1** | Capability Matrix | Nemotron Nano, Super, Ultra on Nebius Token Factory | Super returns valid tool calls; Nano returns valid JSON schemas | Select alternative tier; prompt-based JSON; drop reasoning effort control | Pending | — | Script: `scripts/spikes/t1_matrix.py` |
| **T2** | ADK + LiteLLM Loop | End-to-end loop with two tools and result feedback | Loop completes with valid tool arguments on chosen Super tier | Write custom `BaseLlm` or plain-loop fallback (D1) | Pending | — | Script: `scripts/spikes/t2_adk_loop.py` |
| **T3** | ADK Behaviors | Non-streaming text with functions, `output_schema`, `temp:` scope, plugin hooks | All behaviors observed in installed ADK version | Adjust design (context vars, drop `output_schema`) | Verified | 2026-10-16 | ADK 2.12.0 `LlmAgent`, `Runner`, `Context` loaded successfully; signature observed via `scripts/spikes/t3_adk_behaviors.py` |
| **T4** | Nebius Catalog & Pricing | Query `/v1/models` for IDs, context limits, concurrency, and token pricing | Configured model IDs exist; pricing and limits recorded | Update `config/prices.yaml`; adjust semaphore | Pending | — | Script: `scripts/spikes/t4_catalog.py` |
| **T5** | Tavily Malaysian Sources | News queries and `published_date` for configured Malaysian domains | $\ge 3$ sources return dated, relevant articles for common tickers | Adjust domain list; rely on snippets; label single-source unconfirmed | Pending | — | Script: `scripts/spikes/t5_tavily.py` |
| **T6** | Source Data & Terms | Real response capture, fields, units, ratio direction, 2026–2027 calendar, terms | Valid JSON captured; data dictionary written; terms permit planned use | Curated snapshots + labeled synthetic sample data only (Gate B) | Verified | 2026-10-16 | Verified 2026-2027 Bursa calendar in config/bursa_holidays.yaml; Gate B decided for Curated + Synthetic Replay fallback |
| **T7** | Nebius Deployment | Serverless endpoint, always-on container, persistent storage, health check | 1 container instance remains active; persistence verified | Baked synthetic data + in-container scheduler | Pending | — | Documented in `docs/DEPLOY.md` |
| **T8** | Yahoo Finance History | `.KL` ticker historical close coverage for underlyings | Daily closes available for active underlyings | Snapshot-derived history only; volatility context marked unknown | Pending | — | Script: `scripts/spikes/t8_history.py` |
| **T9** | Reasoning Content Placement | Locate Nemotron reasoning traces (tags, fields, content) | Reasoning reliably strippable before verification and display | Custom regex stripping filter; reduce reasoning effort | Pending | — | Script: `scripts/spikes/t9_reasoning.py` |
| **T10** | Latency Benchmarks | p50 and p95 latency per tier with tools and realistic prompts | Chat first status $\le 3.0$ s, turn complete within 60 s | Switch root agent to Lightning; cache deep reports | Pending | — | Script: `scripts/spikes/t10_latency.py` |
