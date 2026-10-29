"""Structuring and validation of news items into strict schema (T088, FR-NEWS-03, 04, 09).

Enforces:
- Fixed 7-day recency window filter (FR-016).
- Strict length caps: title <= 200 chars, facts <= 3, each fact <= 160 chars.
- Injection defense: strips system override and recommendation prompts.
- Canonical event_type: earnings, contract, dividend, director_dealing, corporate_action, regulatory, macro, other.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import re
from typing import Any

from warrantx.guardrails.injection import detect_prompt_injection, sanitize_external_text

VALID_EVENT_TYPES = {
    "earnings",
    "contract",
    "dividend",
    "director_dealing",
    "corporate_action",
    "regulatory",
    "macro",
    "other",
}


def _parse_pub_date(pub_date: Any) -> datetime | None:
    """Parse ISO-8601 or RFC-2822 published_date into a timezone-aware UTC datetime."""
    if pub_date is None:
        return None
    if isinstance(pub_date, datetime):
        return pub_date if pub_date.tzinfo is not None else pub_date.replace(tzinfo=timezone.utc)
    if isinstance(pub_date, str):
        s = pub_date.strip()
        if not s:
            return None
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass
        try:
            dt = parsedate_to_datetime(s)
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def filter_7day_window(
    items: list[dict[str, Any]],
    reference_time: datetime | None = None,
) -> list[dict[str, Any]]:
    """Filter news items to strictly those within 7 days of the reference time."""
    if reference_time is None:
        parsed_dates = [d for d in (_parse_pub_date(i.get("published_date")) for i in items) if d is not None]
        reference_time = max(parsed_dates) if parsed_dates else datetime.now(timezone.utc)
    elif reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)

    cutoff = reference_time - timedelta(days=7)
    valid_items: list[dict[str, Any]] = []

    for item in items:
        pub_date = item.get("published_date")
        if pub_date is None:
            valid_items.append(item)
            continue

        dt = _parse_pub_date(pub_date)
        if dt is None:
            valid_items.append(item)
            continue

        if dt >= cutoff:
            valid_items.append(item)

    return valid_items


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text).strip()


def _infer_event_type(title: str, content: str) -> str:
    """Infer canonical event_type from title and content when not explicitly provided."""
    blob = f"{title} {content}".lower()
    if any(k in blob for k in ("dividend", "payout", "ex-date", "distribution")):
        return "dividend"
    if any(k in blob for k in ("earnings", "profit", "quarterly", "revenue", "1q", "2q", "3q", "4q", "fy2")):
        return "earnings"
    if any(k in blob for k in ("contract", "award", "tender", "secures", "wins", "letter of award")):
        return "contract"
    if any(k in blob for k in ("director", "shareholding", "insider", "ceo", "board")):
        return "director_dealing"
    if any(k in blob for k in ("acquisition", "merger", "rights issue", "bonus issue", "placement", "privatisation", "mou")):
        return "corporate_action"
    if any(k in blob for k in ("bursa", "securities commission", "bnm", "bank negara", "regulation", "policy")):
        return "regulatory"
    if any(k in blob for k in ("gdp", "inflation", "opr", "ringgit", "fed", "tariff", "economy")):
        return "macro"
    return "other"


def _extract_facts_from_content(content: str) -> list[str]:
    """Split raw Tavily content snippet into up to 3 clean factual sentences."""
    cleaned = _strip_html(content)
    if not cleaned:
        return []
    # Remove markdown table separators, pipes, and URL-encoded SVG/HTML artifacts
    cleaned = re.sub(r"\|[\s\-:|]+\|", " ", cleaned)
    cleaned = re.sub(r"\|+", " ", cleaned)
    cleaned = re.sub(r"%[0-9A-Fa-f]{2}", " ", cleaned)
    cleaned = re.sub(r"\[\.\.\.\]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    parts = [
        p.strip(" -•*:")
        for p in re.split(r"(?<=[.!?])\s+|\n+", cleaned)
        if len(p.strip(" -•*:")) >= 25 and not re.search(r"path\s+d=|sign up for|never miss a post", p, re.I)
    ]
    if not parts and len(cleaned) >= 15:
        parts = [cleaned[:160]]
    return parts[:3]


def _extract_stated_numbers(text: str) -> list[dict[str, str]]:
    """Extract up to 3 stated financial figures (RM or %) from text."""
    results: list[dict[str, str]] = []
    rm_matches = re.findall(r"\bRM\s?\d+(?:[.,]\d+)?(?:\s?(?:bil|billion|mil|million|b|m|k))?\b", text, flags=re.IGNORECASE)
    for m in rm_matches[:2]:
        results.append({"label": "Amount", "text": m.strip()[:40]})
    pct_matches = re.findall(r"\b\d+(?:\.\d+)?%", text)
    for p in pct_matches[:2]:
        if len(results) < 3:
            results.append({"label": "Change", "text": p.strip()[:40]})
    return results


def sanitize_news_item(raw: dict[str, Any]) -> dict[str, Any]:
    """Sanitize and truncate fields to enforce length bounds and injection guards."""
    title = sanitize_external_text(_strip_html(str(raw.get("title", ""))))[:200].strip()
    content_str = str(raw.get("content", "") or "")

    raw_event = str(raw.get("event_type", "") or "").lower()
    if raw_event in VALID_EVENT_TYPES and raw_event != "other":
        event_type = raw_event
    else:
        event_type = _infer_event_type(title, content_str)

    raw_facts = raw.get("facts")
    if not raw_facts and content_str:
        raw_facts = _extract_facts_from_content(content_str)
    elif not isinstance(raw_facts, list):
        raw_facts = []

    clean_facts: list[str] = []
    for f in raw_facts[:3]:
        f_str = _strip_html(str(f))
        if detect_prompt_injection(f_str):
            continue
        sanitized_f = sanitize_external_text(f_str)
        if detect_prompt_injection(sanitized_f):
            continue
        if sanitized_f.strip():
            clean_facts.append(sanitized_f[:160].strip())

    stated_numbers = raw.get("stated_numbers")
    if not stated_numbers and content_str:
        stated_numbers = _extract_stated_numbers(f"{title} {content_str}")

    clean_numbers: list[dict[str, str]] = []
    if isinstance(stated_numbers, list):
        for sn in stated_numbers[:5]:
            if isinstance(sn, dict):
                clean_numbers.append({
                    "label": str(sn.get("label", ""))[:40],
                    "text": str(sn.get("text", ""))[:40],
                })

    pub_dt = _parse_pub_date(raw.get("published_date"))
    pub_iso = pub_dt.isoformat() if pub_dt else raw.get("published_date")

    return {
        "title": title,
        "url": str(raw.get("url", "")),
        "domain": str(raw.get("domain", "")),
        "published_date": pub_iso,
        "retrieved_at": raw.get("retrieved_at", datetime.now(timezone.utc).isoformat()),
        "event_type": event_type,
        "facts": clean_facts,
        "stated_numbers": clean_numbers,
    }
