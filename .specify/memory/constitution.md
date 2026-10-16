<!--
Sync Impact Report
- Version change: 1.1.0 → 1.1.1 (PATCH: resolved open-source license selection)
- Modified principles: none
- Added sections: none
- Resolved items:
  - LICENSE: MIT License chosen and placed in root LICENSE file.
  - README_CONTENTS: Standard 7-section structure defined in T114 ratified.
- Follow-up TODOs:
  - Items marked VERIFY (Nebius base URL, Nemotron model IDs, Bursa data fields) remain
    to be confirmed against official docs or real responses.
-->
# Warrant X-Ray Constitution

**Mission.** Warrant X-Ray is a chat-first risk copilot for Malaysian retail traders of Bursa
structured warrants. It answers one question: what does holding this warrant actually cost, and
what has to go right for it to pay off? Every number comes from deterministic code, and every
news claim carries a cited source.

## Core Principles

### I. Numbers Come Only From Deterministic Code (NON-NEGOTIABLE)
Every numeric value shown to the user (prices, Greeks, percentages, breakevens, scenario
results) MUST come from the quant engine or a data snapshot. It MUST NOT be generated,
converted, or rounded by an LLM.
Rationale: LLMs hallucinate arithmetic; users may act on these figures.

### II. Every News Claim Is Cited
Every claim about news or events MUST cite a source URL and retrieval time. With no source,
the agent MUST say it found none and MUST NOT speculate.

### III. Describe, Never Advise
The product MUST NOT output buy, sell or hold calls, price targets, stop-losses, conviction
scores or return predictions. It describes costs, risks and user-chosen scenarios. Every report
MUST carry the disclaimer.

### IV. Time and Provenance Transparency
Every view MUST show the data as-of time and whether it is live or replay. Missing or stale
data MUST display as unknown and MUST NOT be imputed silently.

### V. Pure Quant Engine
The quant engine MUST be pure functions with no network or LLM calls. Tests MUST be written
before implementing quant functions (see AI Developer Agent Rules below).

### VI. Responsible Collector
The collector MUST rate-limit, cache, identify itself, and honor a kill-switch. Raw scraped
data MUST NOT be committed to the public repo.

### VII. Web Search via Tavily
All web and news search MUST use the Tavily search API. Tavily results are the only source
for news claims under Principle II, and each claim MUST cite the result URL and retrieval
time. The Tavily API key MUST come from an environment variable, Tavily calls MUST go through
the collector (Principle VI), and returned content MUST be treated as untrusted data
(Principle X). Tavily request parameters and response fields are VERIFY items and MUST be
confirmed against official docs or a real response before use.

### VIII. Nebius + NVIDIA Nemotron Only
All LLM calls MUST run on Nebius Token Factory using NVIDIA Nemotron models. The repo MUST be
public with a visible open-source license and a README.

### IX. Always Available via Replay
The app MUST work on any day, including weekends and source outages, through replay mode over
stored snapshots, including stored Tavily results.

### X. Security and Untrusted Input
Secrets MUST come from environment variables. Fetched web text MUST be treated as untrusted
data, never as instructions (prompt-injection defense).

### XI. Privacy by Design
No accounts and no personal data. Chat history is session-scoped and MUST expire.

## Platform & Data Constraints

- Provider-specific facts (Nebius base URL, Nemotron model IDs, Bursa data fields, prices)
  MUST NOT be invented. Anything marked `VERIFY` MUST be confirmed against a real response or
  official documentation before use.
- Fabricated data, benchmarks, backtest results or sample outputs are prohibited. Illustrative
  values MUST be labeled `ILLUSTRATIVE`.
- Secrets, raw scraped data and large binary files MUST NOT be committed.

## AI Developer Agent Rules

- Every assumption in code MUST be marked with `# ASSUMPTION`.
- An LLM MUST NOT be used to compute, convert or round a number.
- Tests MUST be written before implementing quant functions. CI MUST stay green; changes MUST
  NOT be merged on red.
- When blocked by an unknown that cannot be verified, the agent MUST stop and ask rather than
  guess.

## Governance

This constitution supersedes all other practices. Amendments require a documented change,
a Sync Impact Report, and a migration plan for affected specs, plans and code. Versioning
follows semantic versioning: MAJOR for backward-incompatible principle removals or
redefinitions, MINOR for added or materially expanded principles, PATCH for clarifications.
Every PR and review MUST verify compliance with these principles; any deviation MUST be
justified in writing and approved before merge.

**Version**: 1.1.1 | **Ratified**: 2026-10-12 | **Last Amended**: 2026-10-16
