# Warrant X-Ray

[![CI](https://github.com/warrant-xray/warrants-x-ray/actions/workflows/ci.yml/badge.svg)](https://github.com/warrant-xray/warrants-x-ray/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Warrant X-Ray is an educational risk analytics and scenario simulation platform for Malaysian retail traders of Bursa Malaysia structured warrants. It answers one essential question: **what does holding this warrant actually cost, and what has to go right for it to pay off?**

> [!NOTE]
> **Release Status & Feature Notice**:
> - **Chat Function Disabled**: The conversational chat copilot interface is disabled in this release. All functionality is centered around the interactive **Stock Screener**, **Warrant X-Ray Risk Cards**, **Multi-Warrant Comparison**, **7-Day Market News**, and the deterministic **Scenario Simulator**.
> - **Market Data Availability**: Live, real-time intraday tick data from Bursa Malaysia is currently not connected. The application runs on comprehensive synthetic market data fixtures and historical snapshots to demonstrate the quantitative engine, Greeks recalculation, and scenario stress-testing.

Every number shown to the user comes from a deterministic quant engine—LLMs never compute, convert, or round. Every news item cites a verifiable source URL and retrieval timestamp via Tavily Search over a strict 7-day recency window.

**Live Deployment (Google Cloud Run)**: [https://warrant-xray-98064612705.asia-southeast1.run.app](https://warrant-xray-98064612705.asia-southeast1.run.app)

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
Browser (Vite + React SPA: Screener | X-Ray Card | Scenario Simulator | Compare | News)
   │  REST (JSON): /api/warrants, /api/scenario, /api/compare, /api/news
   ▼
+--------------------------- FastAPI App ----------------------------+
|  Middleware: anonymous sessions, daily-salted IP/UA hash, limits   |
|                                                                    |
|  Quant Core (Pure Functions)  <--- Repo (SQLite Snapshots & Data)  |
|  - Black-Scholes pricing           - Append-only snapshots         |
|  - Brent IV solver (Bid/Mid/Ask)   - Normalized warrant rows       |
|  - Holding cost & risk flags       - Replay & Synthetic mode       |
|                                                                    |
|  Data Intelligence & Search                                        |
|  - Tavily Search Gateway (strict 7-day recency, Malaysian domains) |
|  - Nemotron reasoning layer (reserved for Deep Risk Reports)       |
|  - *Chat SSE stream endpoint: currently disabled in this release*   |
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

