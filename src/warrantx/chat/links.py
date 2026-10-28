"""ViewLink data model and link builders for local plain-English chat.

Strictly follows specs/002-local-chat/contracts/chat-links.md and data-model.md.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

LinkKind = Literal["card", "scenario", "compare", "stock", "sources", "health", "news"]


class ViewLink(BaseModel):
    """Deep link to an in-app tab or cited external news article."""

    kind: LinkKind
    label: str
    href: str
    entity: Optional[Dict[str, Any]] = None
    evidence_id: str = ""
    retrieved_at: Optional[str] = None


def build_card_link(code: str, days: int = 5, evidence_id: str = "E1") -> ViewLink:
    """Build a link to the detailed X-Ray warrant card."""
    clamped_days = max(1, min(365, days))
    return ViewLink(
        kind="card",
        label="Open the X-Ray card",
        href=f"/?tab=card&code={code}&days={clamped_days}",
        entity={"code": code},
        evidence_id=evidence_id,
        retrieved_at=None,
    )


def build_scenario_link(code: str, evidence_id: str = "E1") -> ViewLink:
    """Build a link to the scenario simulator for a warrant."""
    return ViewLink(
        kind="scenario",
        label="Try a what-if scenario",
        href=f"/?tab=scenario&code={code}",
        entity={"code": code},
        evidence_id=evidence_id,
        retrieved_at=None,
    )


def build_compare_link(codes: List[str], evidence_id: str = "E1") -> ViewLink:
    """Build a link to compare 2 to 4 warrants side-by-side."""
    joined = ",".join(codes)
    return ViewLink(
        kind="compare",
        label="Compare these warrants",
        href=f"/?tab=compare&codes={joined}",
        entity={"codes": codes},
        evidence_id=evidence_id,
        retrieved_at=None,
    )


def build_stock_link(ticker: str, evidence_id: str = "E1") -> ViewLink:
    """Build a link to all warrants for an underlying stock."""
    return ViewLink(
        kind="stock",
        label="View all warrants for this stock",
        href=f"/?tab=stock&ticker={ticker}",
        entity={"ticker": ticker},
        evidence_id=evidence_id,
        retrieved_at=None,
    )


def build_sources_link(
    code: Optional[str] = None,
    ticker: Optional[str] = None,
    evidence_id: str = "E1",
) -> ViewLink:
    """Build a link to the sources and methodology tab."""
    param = ""
    entity: Dict[str, Any] = {}
    if code:
        param = f"&code={code}"
        entity["code"] = code
    elif ticker:
        param = f"&ticker={ticker}"
        entity["ticker"] = ticker
    return ViewLink(
        kind="sources",
        label="Inspect data sources",
        href=f"/?tab=sources{param}",
        entity=entity if entity else None,
        evidence_id=evidence_id,
        retrieved_at=None,
    )


def build_health_link(evidence_id: str = "E1") -> ViewLink:
    """Build a link to the system health tab."""
    return ViewLink(
        kind="health",
        label="Check system health",
        href="/?tab=health",
        entity=None,
        evidence_id=evidence_id,
        retrieved_at=None,
    )


def build_news_link(
    url: str,
    ticker: str,
    retrieved_at: str,
    evidence_id: str = "E2",
) -> ViewLink:
    """Build a cited external news link."""
    return ViewLink(
        kind="news",
        label="Read coverage (source site)",
        href=url,
        entity={"ticker": ticker},
        evidence_id=evidence_id,
        retrieved_at=retrieved_at,
    )
