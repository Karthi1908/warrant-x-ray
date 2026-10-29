# Warrant X-Ray

[![CI](https://github.com/Karthi1908/warrant-x-ray/actions/workflows/ci.yml/badge.svg)](https://github.com/Karthi1908/warrant-x-ray/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Warrant X-Ray is an educational risk analytics and scenario simulation platform for Malaysian retail traders of Bursa Malaysia structured warrants. It answers one essential question: **what does holding this warrant actually cost, and what has to go right for it to pay off?**

Every number shown to the user comes from a deterministic quant engine—LLMs never compute, convert, or round. Every news item cites a verifiable source URL and retrieval timestamp via Tavily Search over a strict 7-day recency window.

**Live Deployment (Google Cloud Run)**: [https://warrant-xray-98064612705.asia-southeast1.run.app](https://warrant-xray-98064612705.asia-southeast1.run.app)

---

## 1. Mandatory Regulatory Disclaimer

> [!IMPORTANT]
> **REGULATORY DISCLAIMER**: Warrant X-Ray is an informational analytics and mathematical modeling tool designed for retail education and risk awareness. It **does NOT** provide financial, investment, legal, tax, or trading advice. It does not provide buy, sell, or hold recommendations, price targets, entry levels, conviction scores, or return predictions. Structured warrants are complex and high-risk leveraged financial derivatives that may expire worthless, resulting in the total loss of invested capital. Users are solely responsible for their own investment decisions.

---

## 2. Core Features

- **Deterministic Quant Engine**: Pure Python Black-Scholes pricing, Brent implied-volatility solver (Bid/Mid/Ask), holding cost decomposition (bid-ask spread friction + daily theta decay), and issuer-vs-quant discrepancy flags.
- **Interactive Scenario Simulator & Multi-Warrant Compare**: Real-time stress testing across spot price moves, holding horizons, and IV shifts, plus side-by-side comparison across effective gearing, spread friction, and time decay.
- **NVIDIA Nemotron Reasoning (via Nebius Token Factory)**: Three-tier routing (`Nemotron-3-Nano`, `Super`, and `Ultra`) with automatic circuit breakers and daily USD budget caps powering adversarial Red-Team Review in 4-Stage Deep Risk Reports.
- **Risk Copilot Chat**: Plain-English conversational copilot enforced by a zero-number verify-before-stream guardrail, bilingual (English / Bahasa Melayu) advice refusal, and interactive deep-link chips (`card`, `scenario`, `compare`, `stock`, `news`).
- **Tavily 7-Day Market Intelligence & Screener Crawl**: Grounded 7-day Bursa Malaysia news search and content extraction with prompt-injection sanitization, multi-domain corroboration, 30-minute SQLite caching, and automated warrant screener crawling with direct fallback.

---

## 3. Setup & Run Instructions

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

## 4. System Architecture

```text
Browser (Vite + React SPA: Screener | X-Ray Card | Scenario Simulator | Compare | News | Chat)
   │  REST (JSON) & SSE: /api/warrants, /api/scenario, /api/compare, /api/news, /api/report, /api/chat
   ▼
+--------------------------------- FastAPI App ----------------------------------+
|  Middleware: anonymous sessions, daily-salted IP/UA hash, rate & budget limits |
|                                                                                |
|  Quant Core (Pure Functions)        <--- Repo (SQLite Snapshots & Persistence) |
|  - Black-Scholes pricing                 - Append-only market snapshots        |
|  - Brent IV solver (Bid/Mid/Ask)         - Normalized warrant & underlying DB  |
|  - Holding cost & risk flags             - 30-min news cache & replay sets     |
|                                                                                |
|  AI Reasoning & Grounded Search                                                |
|  - NVIDIA Nemotron (Nebius Token Factory: Nano / Super / Ultra + circuit brkr) |
|  - Tavily Search, Extract & Crawl (strict 7-day recency, domain corroboration) |
|  - Verify-Before-Stream Guardrails (zero-number chat, EN/BM advice refusal)    |
+--------------------------------------------------------------------------------+
```

---

## 5. Model Usage & Cost Tracking

Costs are tracked per tier in SQLite (`llm_calls` and `budget_ledger`) without storing personal data or raw IP addresses. Run `uv run python scripts/cost_report.py` to view live token and cost totals by model tier and date.

---

## 6. Open-Source License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.
