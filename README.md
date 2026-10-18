# Warrant X-Ray

[![CI](https://github.com/warrant-xray/warrants-x-ray/actions/workflows/ci.yml/badge.svg)](https://github.com/warrant-xray/warrants-x-ray/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Warrant X-Ray is a chat-first risk copilot for Malaysian retail traders of Bursa Malaysia structured warrants. It answers one question: **what does holding this warrant actually cost, and what has to go right for it to pay off?**

Every number shown to the user comes from a deterministic quant engine or verified market snapshot—LLMs never compute, convert, or round. Every news claim cites a verifiable source URL and retrieval time via Tavily Search over a strict 7-day recency window.

---

## 1. Mandatory Regulatory Disclaimer

> [!IMPORTANT]
> **REGULATORY DISCLAIMER**: Warrant X-Ray is an informational analytics and mathematical modeling tool designed for retail education and risk awareness. It **does NOT** provide financial, investment, legal, tax, or trading advice. It does not provide buy, sell, or hold recommendations, price targets, entry levels, conviction scores, or return predictions. Structured warrants are complex and high-risk leveraged financial derivatives that may expire worthless, resulting in the total loss of invested capital. Users are solely responsible for their own investment decisions.

---

## 2. Setup & Run Instructions

### Prerequisites
- Python 3.11+
- Node.js 20+ (with npm)
- [uv](https://github.com/astral-sh/uv) package manager
- Docker (optional, for containerized run)

### Local Development Setup

1. **Clone the repository and prepare environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials (WX_NEBIUS_API_KEY, WX_TAVILY_API_KEY, etc.)
   ```

2. **Backend**:
   ```bash
   uv sync
   uv run uvicorn warrantx.api.app:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Frontend (Vite + React SPA)**:
   ```bash
   cd web
   npm install
   npm run dev
   ```
   Open `http://localhost:5173` in your browser.

### Docker Run
```bash
docker compose up --build
```
Access the application at `http://localhost:8000`.

---

## 3. System Architecture

```text
Browser (Vite + React SPA)
   │  REST (JSON)                 │  POST /api/chat (SSE stream)
   ▼                              ▼
+--------------------------- FastAPI App ----------------------------+
|  Middleware: anonymous sessions, daily-salted IP/UA hash, limits   |
|                                                                    |
|  Quant Core (Pure Functions)  <--- Repo (SQLite Snapshots & Data)  |
|  - Black-Scholes pricing           - Append-only snapshots         |
|  - Brent IV solver (5 bases)       - Normalized warrant rows       |
|  - Holding cost & risk flags       - Replay mode                   |
|                                                                    |
|  Agent Orchestration (Google ADK)                                  |
|  - Root Agent (Nemotron Super)     - Tavily Gateway (7-day window) |
|  - Deep Report (Nemotron Ultra)    - Verify-Before-Stream Guard    |
+--------------------------------------------------------------------+
```

---

## 4. Open-Source License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## 5. Verified vs. Unverified Status

Following Constitution Principle IV and AI Developer Agent Rules, unverified external parameters are never treated as facts until confirmed via verification spikes:

| Area | Status | Verification Protocol |
|:---|:---:|:---|
| **Quant Engine Formulas** | Verified | Unit tests against golden values, put-call parity, and Brent IV round-trip |
| **Bursa Trading Calendar** | Pending T013 | 2026 & 2027 calendars to be verified via official Bursa circulars |
| **Token Factory Tool Calling** | Pending T009 | Capability matrix spike against Nebius Token Factory endpoints |
| **Tavily Malaysian Sources** | Pending T015 | Top Malaysian financial domains benchmarked for news citations |

---

## 6. Model Usage & Cost Table (from `scripts/cost_report.py`)

Costs are tracked per tier and logged in SQLite without storing user personal data or raw IP addresses.

### LLM Usage by Tier (AC-19)
| Tier  | Calls | In Tokens | Out Tokens | Cost USD  |
|:------|:------|:----------|:-----------|:----------|
| ultra | 4     | 2,000     | 600        | $0.001800 |

### Daily LLM Cost Breakdown
| Date       | Calls | In Tokens | Out Tokens | Avg Latency (ms) | Cost USD  |
|:-----------|:------|:----------|:-----------|:-----------------|:----------|
| 2026-10-17 | 3     | 1,500     | 450        | 1200.0           | $0.001350 |
| 2026-10-18 | 1     | 500       | 150        | 1200.0           | $0.000450 |

*Run `uv run python scripts/cost_report.py` to refresh live totals.*

