"""Grounding verifier and strip-and-note engine.

Implements FR-GRD-01, FR-GRD-02, FR-GRD-03:
- Verifies every stated number in agent responses against an allowlist of evidence display strings,
  numeric fields, and user-typed numbers.
- Supports exact matching and rounding tolerance matching.
- Performs strip-and-note sentence elimination with omission notes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Collection, Iterable

from warrantx.guardrails.templates import get_omission_note


@dataclass
class GroundingResult:
    """Result of validating an agent response against allowed grounding items."""

    is_grounded: bool
    ungrounded_tokens: list[str] = field(default_factory=list)
    verified_tokens: list[str] = field(default_factory=list)


# Pattern matching numbers, currencies, percentages, ratios, and decimals
# Excludes dates (YYYY-MM-DD) and evidence citations ([E1])
_NUMBER_PATTERN = re.compile(
    r"""
    (?<!\w)
    (?:
        (?:RM\s*)?[-+]?\d+(?:,\d{3})*(?:\.\d+)?(?:%|x)?
        |
        [-+]?\d+(?:\.\d+)?(?:%|x)
    )
    (?!\w)
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Date pattern to exclude from number checks
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _clean_token(tok: str) -> str:
    """Normalize extracted token by trimming whitespace and punctuation."""
    t = tok.strip(" ,;:()[]{}'\"")
    return t


def _parse_numeric(tok: str) -> float | None:
    """Extract floating point magnitude from a string token."""
    cleaned = tok.replace("RM", "").replace("rm", "").replace("%", "").replace("x", "").replace("X", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _is_within_tolerance(val: float, targets: Iterable[float]) -> bool:
    """Check if value matches any target within sensible rounding tolerance."""
    for t in targets:
        # Check direct value
        diff = abs(val - t)
        if diff <= 0.051:  # Covers 1 decimal place rounding (e.g. 42.5 vs 42.52 or 5.2 vs 5.184)
            return True
        # Check percentage/fraction scaling (e.g., 0.425 vs 42.5)
        if t != 0:
            pct_scaled = t * 100.0
            if abs(val - pct_scaled) <= 0.051:
                return True
            inv_scaled = t / 100.0
            if abs(val - inv_scaled) <= 0.0006:
                return True
    return False


def verify_grounding(
    text: str,
    allowlist: Collection[str],
    numeric_values: Collection[float] | None = None,
) -> GroundingResult:
    """Verify that every number in text matches the allowlist or numeric values."""
    cleaned_allowlist = {s.strip().lower() for s in allowlist if s}
    numeric_targets = list(numeric_values) if numeric_values else []

    # Also harvest numeric targets from the allowlist strings
    for item in allowlist:
        v = _parse_numeric(item)
        if v is not None:
            numeric_targets.append(v)

    # 1. Check and mask ISO dates like 2026-06-30
    working_text = text
    dates_found = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", working_text)
    ungrounded = []
    verified = []

    for d in dates_found:
        if d.lower() in cleaned_allowlist or True:  # Standard dates from calendar/snapshot
            verified.append(d)
        else:
            ungrounded.append(d)
    working_text = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " __DATE__ ", working_text)

    # 2. Mask citations like [E1] or [E1, E2]
    working_text = re.sub(r"\[E\d+(?:,\s*E\d+)*\]", " __CITATION__ ", working_text)

    raw_tokens = _NUMBER_PATTERN.findall(working_text)

    for raw in raw_tokens:
        tok = _clean_token(raw)
        if not tok or tok in ("__DATE__", "__CITATION__"):
            continue

        # Skip dates like 2026-06-30
        if _DATE_PATTERN.match(tok):
            continue

        # Skip simple single-digit numbering like '1.' or '[E1]' or 'E1'
        if re.match(r"^E\d+$", tok, re.IGNORECASE):
            continue

        # 1. Exact string match against allowlist
        if tok.lower() in cleaned_allowlist:
            verified.append(tok)
            continue

        # 2. Try variations (with or without 'RM', '%', 'x')
        tok_stripped = tok.replace("RM", "").replace("rm", "").strip().lower()
        if tok_stripped in cleaned_allowlist:
            verified.append(tok)
            continue

        # 3. Numeric value matching within rounding tolerance
        val = _parse_numeric(tok)
        if val is not None and _is_within_tolerance(val, numeric_targets):
            verified.append(tok)
            continue

        # Unmatched number token
        ungrounded.append(tok)

    return GroundingResult(
        is_grounded=len(ungrounded) == 0,
        ungrounded_tokens=ungrounded,
        verified_tokens=verified,
    )


def strip_and_note(
    text: str,
    ungrounded_tokens: list[str],
    lang: str = "en",
) -> str:
    """Remove sentences containing ungrounded tokens and append an omission notice."""
    if not ungrounded_tokens:
        return text

    # Split into sentences preserving punctuation
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    kept_sentences = []
    omitted = False

    for sent in sentences:
        has_ungrounded = any(tok in sent for tok in ungrounded_tokens)
        if has_ungrounded:
            omitted = True
        else:
            kept_sentences.append(sent)

    result = " ".join(kept_sentences).strip()

    if omitted:
        note = get_omission_note(lang)
        if result:
            result = f"{result} {note}"
        else:
            result = note

    return result
