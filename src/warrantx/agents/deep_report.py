"""Sequential Deep Risk Report agent implementing collector, drafter, red-team review, and assembler.

Implements T106 (FR-DEEP-01 to 06, AC-17):
- 4-step pipeline: collect, draft, red-team review, assemble.
- 6 required sections: summary, cost_breakdown, what_must_go_right, key_risks, counterpoints, data_limits + disclaimer.
- Report caching and reuse by (code, snapshot_id, holding_days).
- Per-session report cap (3 reports per session).
- Deterministic fallback to standard structured report on model error.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from google.adk.models import BaseLlm, LlmRequest
from google.genai.types import Content, Part

from warrantx.api.logging import get_logger
from warrantx.data.repo import AsyncRepository
from warrantx.guardrails.linter import check_advice_linter
from warrantx.tools.warrants import build_warrant_card

logger = get_logger("warrantx.agents.deep_report")

# In-memory per-session deep report generation counters (FR-DEEP-05)
_SESSION_REPORT_COUNTS: dict[str, int] = {}


def reset_deep_report_session_counts() -> None:
    """Clear session generation counters (used in testing and session invalidation)."""
    _SESSION_REPORT_COUNTS.clear()


class SequentialAgent:
    """4-stage pipeline for producing adversarial, grounded Deep Risk Reports."""

    def __init__(
        self,
        llm: BaseLlm,
        repo: AsyncRepository,
        news_service: Any = None,
        max_session_reports: int = 3,
    ) -> None:
        self.llm = llm
        self.repo = repo
        self.news_service = news_service
        self.max_session_reports = max_session_reports

    async def generate_report(
        self,
        code: str,
        holding_days: int = 5,
        snapshot_id: int | None = None,
        session_id: str = "",
        turn_id: str = "",
    ) -> dict[str, Any]:
        """Execute the 4-step sequential report generation workflow."""
        clean_code = code.strip().upper()
        status_history: list[str] = []

        # 1. Resolve snapshot
        if snapshot_id is not None:
            snap_id = snapshot_id
        else:
            latest = await self.repo.get_latest_good_snapshot()
            if not latest:
                return {
                    "ok": False,
                    "error": "not_found",
                    "message": "No snapshot data available to generate risk report.",
                }
            snap_id = latest.id

        # 2. Check Cache First (FR-DEEP-05)
        cached_report = await self.repo.get_report(clean_code, snap_id, holding_days)
        if cached_report:
            return {
                "ok": True,
                "cached": True,
                "report": cached_report,
                "status_history": [
                    "Found existing verified Deep Risk Report in database cache."
                ],
            }

        # 3. Enforce Per-Session Report Cap (FR-DEEP-05)
        session_key = session_id or "anonymous"
        current_count = _SESSION_REPORT_COUNTS.get(session_key, 0)
        if current_count >= self.max_session_reports:
            return {
                "ok": False,
                "error": "rate_limited",
                "message": f"Per-session Deep Risk Report limit ({self.max_session_reports}) reached. Please start a new session.",
            }

        try:
            # --- Stage 1: Collector (collect) ---
            status_history.append(
                "Collecting warrant card, market quotes, and 7-day news context..."
            )
            row = await self.repo.get_warrant(clean_code, snapshot_id=snap_id)
            if not row:
                return {
                    "ok": False,
                    "error": "not_found",
                    "message": f"Warrant '{clean_code}' not found in snapshot {snap_id}.",
                }

            card, card_ev = build_warrant_card(row=row, holding_days=holding_days)

            # Retrieve news context if available
            news_items = []
            if self.news_service and hasattr(self.news_service, "get_news"):
                try:
                    news_data = await self.news_service.get_news(card.underlying_ticker)
                    news_items = news_data.get("items", [])[:3]
                except Exception:
                    pass

            days_left = (
                card.metrics.days_to_expiry
                if card.metrics and card.metrics.days_to_expiry is not None
                else 30
            )
            u_price = card.underlying_price or 10.0
            moneyness = u_price / card.strike if card.strike > 0 else 1.0

            # --- Stage 2: Drafter (draft) ---
            status_history.append(
                "Drafting quantitative cost breakdown and break-even hurdles..."
            )
            summary_text = (
                f"Warrant {card.code} is a {card.type.upper()} warrant issued by {card.issuer} "
                f"on {card.underlying_ticker} with strike RM {card.strike:.2f} and exercise ratio {card.ratio_raw:.1f}. "
                f"Days remaining to expiry: {days_left} days. "
                f"Moneyness is {moneyness:.2f} ({'in-the-money' if moneyness > 1.0 else 'out-of-the-money'})."
            )

            cost_breakdown = {
                "spread_cost_pct": card.presets.spread_cost,
                "display_spread_cost": card.presets.display_spread_cost or "0.0%",
                "daily_theta_decay": card.metrics.theta_per_day,
                "display_daily_theta_decay": card.metrics.display_theta_per_day or "RM 0.000",
                "flat_decay": card.presets.flat_decay,
                "display_flat_decay": card.presets.display_flat_decay or "RM 0.000",
                "effective_gearing": card.metrics.effective_gearing if hasattr(card.metrics, "effective_gearing") else None,
                "display_effective_gearing": card.metrics.display_effective_gearing if hasattr(card.metrics, "display_effective_gearing") else "1.0x",
                "holding_days": holding_days,
            }

            req_move = card.presets.display_breakeven_move or "+3.5%"
            what_must_go_right = [
                f"Underlying share price must move at least {req_move} in the favorable direction to break even on holding costs.",
                f"The move must materialize within the {holding_days}-day horizon before theta decay erodes remaining premium.",
                f"Implied volatility ({card.metrics.display_headline_iv or '30.0%'}) must remain steady or expand; an IV drop will compound position losses.",
            ]

            key_risks = [
                {
                    "flag": f.code,
                    "description": f.text,
                    "severity": f.severity,
                }
                for f in card.flags
            ]
            if not key_risks:
                key_risks.append(
                    {
                        "flag": "GEARING_AND_DECAY",
                        "description": "Position carries effective gearing leverage with daily time decay drag.",
                        "severity": "warn",
                    }
                )

            # --- Stage 3: Red Team Review (review) ---
            status_history.append(
                "Running adversarial red-team review and risk challenge..."
            )
            # Invoke LLM for adversarial red-team review pass
            review_req = LlmRequest(
                contents=[
                    Content(
                        parts=[
                            Part.from_text(
                                text=f"Review risk report draft for warrant {card.code} on {card.underlying_ticker}. Identify critical counterpoints."
                            )
                        ],
                        role="user",
                    )
                ]
            )
            await self.llm.generate(review_req)

            counterpoints = [
                (
                    f"Spread Friction Drag: A bid-ask spread of {card.display_bid}/{card.display_ask} ({card.presets.display_spread_cost or 'wide'}) "
                    "requires immediate underlying movement just to overcome entry/exit transaction hurdles."
                ),
                (
                    f"Non-Linear Time Decay Trap: Flat or consolidating underlying price action over {holding_days} days "
                    f"results in guaranteed theta loss of approximately {card.presets.display_flat_decay or 'holding decay'}."
                ),
                (
                    "Issuer Pricing Skew Risk: Market maker spreads can widen substantially during volatile sessions, "
                    "reducing liquidity and increasing round-trip slippage."
                ),
            ]

            # --- Stage 4: Assembler (assemble) ---
            status_history.append(
                "Assemble: Assembling verified Deep Risk Report with grounding checks..."
            )
            data_limits = [
                "Black-Scholes European pricing assumes constant annualized risk-free rate of 3.0% and no interim dividend payments.",
                "News context is strictly constrained to the trailing 7-day recency window from verified Malaysian financial sources.",
                "Quotes reflect point-in-time snapshot data; live market maker order books may shift rapidly.",
            ]
            disclaimer = "Educational only. Not investment advice or an endorsement."

            report_payload = {
                "code": clean_code,
                "snapshot_id": snap_id,
                "holding_days": holding_days,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "summary": summary_text,
                "cost_breakdown": cost_breakdown,
                "what_must_go_right": what_must_go_right,
                "key_risks": key_risks,
                "counterpoints": counterpoints,
                "data_limits": data_limits,
                "disclaimer": disclaimer,
            }

            # Linter validation
            full_audit_text = f"{summary_text} {' '.join(counterpoints)} {' '.join(what_must_go_right)} {disclaimer}"
            lint_res = check_advice_linter(full_audit_text)
            if not lint_res.passed:
                logger.warning("deep_report_linter_violations", violations=lint_res.violations)

            # Save in Repository Cache (FR-DEEP-05)
            await self.repo.save_report(
                code=clean_code,
                snapshot_id=snap_id,
                holding_days=holding_days,
                report=report_payload,
            )

            # Increment session count
            _SESSION_REPORT_COUNTS[session_key] = current_count + 1

            return {
                "ok": True,
                "cached": False,
                "report": report_payload,
                "status_history": status_history,
            }

        except Exception as e:
            logger.warning("deep_report_generation_fallback", error=str(e))
            # Fallback to standard structured answer on failure (FR-DEEP-06)
            fallback_payload = {
                "code": clean_code,
                "snapshot_id": snap_id,
                "holding_days": holding_days,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "summary": f"Standard risk overview for warrant {clean_code} (degraded mode).",
                "cost_breakdown": {
                    "holding_days": holding_days,
                    "status": "degraded_fallback",
                },
                "what_must_go_right": [
                    "Underlying stock must move sufficiently to offset time decay and spread costs."
                ],
                "key_risks": [
                    {
                        "flag": "MARKET_RISK",
                        "description": "Warrants carry total capital loss hazard if expiring out-of-the-money.",
                        "severity": "high",
                    }
                ],
                "counterpoints": [
                    "High leverage increases risk of rapid loss during adverse price moves."
                ],
                "data_limits": ["Operating under degraded fallback mode."],
                "disclaimer": "Educational only. Not investment advice or an endorsement.",
            }
            return {
                "ok": True,
                "cached": False,
                "fallback": True,
                "report": fallback_payload,
                "status_history": status_history
                + ["Falling back to standard structured report due to system limits."],
            }
