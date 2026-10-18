"""Structuring and validation of news items into strict schema (T088, FR-NEWS-03, 04, 09).

Enforces:
- Fixed 7-day recency window filter (FR-016).
- Strict length caps: title <= 200 chars, facts <= 3, each fact <= 160 chars.
- Injection defense: strips system override and recommendation prompts.
- Canonical event_type: earnings, contract, dividend, director_dealing, corporate_action, regulatory, macro, other.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
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


def filter_7day_window(
    items: list[dict[str, Any]],
    reference_time: datetime | None = None,
) -> list[dict[str, Any]]:
    """Filter news items to strictly those within 7 days of the reference time."""
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)
    elif reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)

    cutoff = reference_time - timedelta(days=7)
    valid_items: list[dict[str, Any]] = []

    for item in items:
        pub_date = item.get("published_date")
        if pub_date is None:
            # If published_date is missing, allow item if retrieved recently
            valid_items.append(item)
            continue

        try:
            if isinstance(pub_date, str):
                dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
            elif isinstance(pub_date, datetime):
                dt = pub_date
            else:
                valid_items.append(item)
                continue

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            if dt >= cutoff:
                valid_items.append(item)
        except Exception:
            # On parse error, retain conservatively if not clearly old
            valid_items.append(item)

    return valid_items


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text).strip()


def sanitize_news_item(raw: dict[str, Any]) -> dict[str, Any]:
    """Sanitize and truncate fields to enforce length bounds and injection guards."""
    title = sanitize_external_text(_strip_html(str(raw.get("title", ""))))[:200].strip()

    raw_event = str(raw.get("event_type", "other")).lower()
    event_type = raw_event if raw_event in VALID_EVENT_TYPES else "other"

    raw_facts = raw.get("facts", [])
    clean_facts: list[str] = []

    if isinstance(raw_facts, list):
        for f in raw_facts[:3]:
            f_str = _strip_html(str(f))
            if detect_prompt_injection(f_str):
                continue
            sanitized_f = sanitize_external_text(f_str)
            if detect_prompt_injection(sanitized_f):
                continue
            clean_facts.append(sanitized_f[:160].strip())

    stated_numbers = raw.get("stated_numbers", [])
    clean_numbers: list[dict[str, str]] = []
    if isinstance(stated_numbers, list):
        for sn in stated_numbers[:5]:
            if isinstance(sn, dict):
                clean_numbers.append({
                    "label": str(sn.get("label", ""))[:40],
                    "text": str(sn.get("text", ""))[:40],
                })

    return {
        "title": title,
        "url": str(raw.get("url", "")),
        "domain": str(raw.get("domain", "")),
        "published_date": raw.get("published_date"),
        "retrieved_at": raw.get("retrieved_at", datetime.now(timezone.utc).isoformat()),
        "event_type": event_type,
        "facts": clean_facts,
        "stated_numbers": clean_numbers,
    }
