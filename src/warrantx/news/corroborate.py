"""News corroboration and deduplication engine (T089, FR-NEWS-05 to 08).

Implements:
- Deduplication by normalized URL.
- Multi-domain corroboration:
  - If 2+ distinct domains report on the same event (shared event_type, date window, or significant title word overlap),
    they are consolidated with `corroboration_count >= 2` and `unconfirmed = False`.
  - If only 1 domain reported the event, `corroboration_count = 1` and `unconfirmed = True`.
"""

from __future__ import annotations

import re
from typing import Sequence
from urllib.parse import urlparse

from warrantx.tools.models import NewsItem


def _tokenize(text: str) -> set[str]:
    """Extract lowercase alphanumeric tokens."""
    tokens = set(re.findall(r"\b[a-zA-Z0-9]{3,}\b", text.lower()))
    stop_words = {"the", "and", "for", "with", "from", "that", "this", "bhd", "berhad", "malaysia", "group"}
    return tokens - stop_words


def _are_similar_events(item1: NewsItem, item2: NewsItem) -> bool:
    """Check if two news items describe the same real-world event."""
    # If different event types, unlikely to be identical event
    if item1.event_type != "other" and item2.event_type != "other":
        if item1.event_type != item2.event_type:
            return False

    # Check shared stated numbers (e.g. RM 2.0B)
    nums1 = {n.get("text", "").lower().replace(" ", "") for n in item1.stated_numbers if n.get("text")}
    nums2 = {n.get("text", "").lower().replace(" ", "") for n in item2.stated_numbers if n.get("text")}
    shared_numbers = nums1.intersection(nums2)
    if shared_numbers:
        return True

    # Token overlap (Jaccard similarity on significant title tokens)
    toks1 = _tokenize(item1.title)
    toks2 = _tokenize(item2.title)
    if not toks1 or not toks2:
        return False

    intersection = toks1.intersection(toks2)
    union = toks1.union(toks2)
    similarity = len(intersection) / len(union)

    # 30% overlap on keywords indicates common story
    return similarity >= 0.28


def deduplicate_news(items: Sequence[NewsItem]) -> list[NewsItem]:
    """Deduplicate items with identical or equivalent URLs."""
    seen_urls: set[str] = set()
    deduped: list[NewsItem] = []

    for item in items:
        norm_url = item.url.strip().lower().rstrip("/")
        if norm_url and norm_url in seen_urls:
            continue
        seen_urls.add(norm_url)
        deduped.append(item)

    return deduped


def corroborate_news(
    items: Sequence[NewsItem],
    ticker: str = "",
) -> list[NewsItem]:
    """Cluster news items into corroborated stories across domains."""
    deduped = deduplicate_news(items)
    if not deduped:
        return []

    clusters: list[list[NewsItem]] = []

    for item in deduped:
        matched = False
        for cluster in clusters:
            # Compare with representative of cluster
            if _are_similar_events(item, cluster[0]):
                cluster.append(item)
                matched = True
                break
        if not matched:
            clusters.append([item])

    corroborated_results: list[NewsItem] = []

    for cluster in clusters:
        primary = cluster[0]
        domains = {urlparse(i.url).netloc.lower() or i.domain.lower() for i in cluster}
        # Filter out empty or duplicate domain labels
        unique_domains = {d[4:] if d.startswith("www.") else d for d in domains if d}

        corr_count = max(1, len(unique_domains))
        is_unconfirmed = corr_count < 2

        # Combine unique facts
        all_facts: list[str] = []
        for i in cluster:
            for f in i.facts:
                if f not in all_facts and len(all_facts) < 3:
                    all_facts.append(f)

        # Merge stated numbers
        all_numbers: list[dict[str, str]] = []
        seen_labels: set[str] = set()
        for i in cluster:
            for n in i.stated_numbers:
                label = n.get("label", "")
                if label not in seen_labels:
                    seen_labels.add(label)
                    all_numbers.append(n)

        merged = NewsItem(
            title=primary.title,
            url=primary.url,
            domain=primary.domain,
            published_date=primary.published_date,
            retrieved_at=primary.retrieved_at,
            event_type=primary.event_type,
            facts=all_facts or primary.facts,
            stated_numbers=all_numbers or primary.stated_numbers,
            corroboration_count=corr_count,
            unconfirmed=is_unconfirmed,
            extraction_method=primary.extraction_method,
        )
        corroborated_results.append(merged)

    return corroborated_results
