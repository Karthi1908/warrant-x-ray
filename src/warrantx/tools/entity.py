"""Entity resolution tool for Bursa Malaysia underlyings and stock codes.

Implements FR-NAME-01, FR-NAME-02, FR-NAME-03, FR-NAME-04, AC-06:
- Exact matching on ticker, Bursa numeric stock code, and company name.
- Rapidfuzz-backed typo and partial name matching.
- Ambiguity detection when multiple candidates match closely.
- Suggestions fallback when no close match is found.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field
from rapidfuzz import fuzz


class EntityMatchResult(BaseModel):
    """Result of resolving a company name or ticker to an underlying entity."""

    status: str  # "exact" | "fuzzy" | "ambiguous" | "not_found"
    matched_ticker: str | None = None
    matched_code: str | None = None
    matched_name: str | None = None
    confidence: float = 0.0
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


def resolve_entity(
    query: str,
    candidates: list[dict[str, Any]] | None = None,
) -> EntityMatchResult:
    """Resolve an arbitrary user query string to a validated underlying stock entity."""
    q = query.strip()
    if not q:
        return EntityMatchResult(status="not_found", confidence=0.0)

    if not candidates:
        return EntityMatchResult(status="not_found", confidence=0.0)

    q_upper = q.upper()

    # Check if multiple entities share this primary name prefix (e.g. Genting Berhad vs Genting Malaysia)
    prefix_candidates = [
        c for c in candidates
        if c.get("name", "").upper().startswith(q_upper) or c.get("ticker", "").upper().startswith(q_upper)
    ]
    if len(prefix_candidates) > 1:
        return EntityMatchResult(
            status="ambiguous",
            confidence=0.95,
            candidates=prefix_candidates,
            suggestions=[c.get("ticker", "") for c in prefix_candidates[:3]],
        )

    # 1. Exact match by ticker, stock code, or name
    for c in candidates:
        ticker = c.get("ticker", "").strip().upper()
        code = str(c.get("code", "")).strip()
        name = c.get("name", "").strip().upper()

        if q_upper == ticker or q == code or q_upper == name:
            return EntityMatchResult(
                status="exact",
                matched_ticker=c.get("ticker"),
                matched_code=code,
                matched_name=c.get("name"),
                confidence=1.0,
                candidates=[c],
            )

    # 2. Fuzzy matching across all candidates
    scored: list[tuple[float, dict[str, Any]]] = []

    for c in candidates:
        ticker = c.get("ticker", "").strip()
        code = str(c.get("code", "")).strip()
        name = c.get("name", "").strip()

        score_ticker = fuzz.ratio(q_upper, ticker.upper())
        score_name_sort = fuzz.token_sort_ratio(q, name)
        score_name_partial = fuzz.partial_ratio(q.lower(), name.lower())
        score_code = fuzz.ratio(q, code)

        best_score = max(score_ticker, score_name_sort, score_name_partial, score_code)
        scored.append((best_score, c))

    scored.sort(key=lambda x: x[0], reverse=True)

    top_score, top_candidate = scored[0]

    # Check for ambiguity: multiple candidates with high and close scores (>= 75% and within 8 pts)
    high_matches = [
        c for score, c in scored if score >= 75.0 and abs(score - top_score) <= 8.0
    ]

    if len(high_matches) > 1 and top_score >= 75.0:
        return EntityMatchResult(
            status="ambiguous",
            confidence=round(top_score / 100.0, 2),
            candidates=high_matches,
            suggestions=[c.get("ticker", "") for c in high_matches[:3]],
        )

    if top_score >= 75.0:
        return EntityMatchResult(
            status="fuzzy",
            matched_ticker=top_candidate.get("ticker"),
            matched_code=str(top_candidate.get("code", "")),
            matched_name=top_candidate.get("name"),
            confidence=round(top_score / 100.0, 2),
            candidates=[top_candidate],
        )

    # 3. Not found: return top suggestions
    suggestions = [c.get("ticker", "") for _, c in scored[:3] if c.get("ticker")]
    return EntityMatchResult(
        status="not_found",
        confidence=round(top_score / 100.0, 2),
        suggestions=suggestions,
    )
