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
    # 0. Normalize unicode characters (non-breaking spaces, unicode hyphens, minuses)
    working_text = (
        text.replace("\u202f", " ")
        .replace("\u00a0", " ")
        .replace("\u2011", "-")
        .replace("\u2010", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2015", "-")
        .replace("\u2212", "-")
    )

    cleaned_allowlist = {s.strip().lower() for s in allowlist if s}
    numeric_targets = list(numeric_values) if numeric_values else []

    # Also harvest numeric targets from the allowlist strings
    for item in allowlist:
        v = _parse_numeric(item)
        if v is not None:
            numeric_targets.append(v)

    # 1. Check and mask dates in all formats
    working_text = re.sub(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", " __DATE__ ", working_text)
    working_text = re.sub(
        r"\b(?:\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b",
        " __DATE__ ",
        working_text,
        flags=re.IGNORECASE,
    )

    # 2. Mask citations like [E1] or [E1, E2]
    working_text = re.sub(r"\[E\d+(?:,\s*E\d+)*\]", " __CITATION__ ", working_text)

    # 3. Mask alphanumeric warrant codes (e.g. 1155A1, 115510, 0166A1)
    working_text = re.sub(r"\b\d{4}[A-Za-z0-9]{1,4}\b", " __CODE__ ", working_text)

    raw_tokens = _NUMBER_PATTERN.findall(working_text)
    ungrounded = []
    verified = []

    for raw in raw_tokens:
        tok = _clean_token(raw)
        if not tok or tok in ("__DATE__", "__CITATION__", "__CODE__"):
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
        has_ungrounded = False
        for tok in ungrounded_tokens:
            escaped_tok = re.escape(tok)
            pattern = rf"(?<![\w]){escaped_tok}(?![\w]|(?<=\d)\.\d)"
            if re.search(pattern, sent):
                has_ungrounded = True
                break
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


# ---------------------------------------------------------------------------
# Plain-English chat policy (spec 002-local-chat, FR-LC-03):
# prose must contain no figures at all. Numbers live behind links.
# ---------------------------------------------------------------------------

# ASSUMPTION: English number words are the relevant leak vector for the English prose path.
_NUMBER_WORDS = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
    "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
    "eighty", "ninety", "hundred", "thousand", "million", "billion",
    "half", "halves", "double", "triple", "twice", "thrice", "percent",
)
_NUMBER_WORD_PATTERN = re.compile(r"\b(?:" + "|".join(_NUMBER_WORDS) + r")\b", re.IGNORECASE)
_PER_CENT_PATTERN = re.compile(r"\bper\s+cent\b", re.IGNORECASE)
_FIGURE_PATTERN = re.compile(r"(?:RM\s*)?[-+]?\d+(?:[.,/]\d+)*(?:%|x\b)?|%", re.IGNORECASE)


@dataclass
class NumberCheckResult:
    """Outcome of the no-numbers check on plain-English chat prose."""

    passed: bool
    offending_tokens: list[str] = field(default_factory=list)


def verify_no_numbers(
    text: str,
    allowed_tokens: Iterable[str] | None = None,
) -> NumberCheckResult:
    """Reject any digit, figure, currency amount, percentage or number word in ``text``.

    ``allowed_tokens`` are identifiers or user-typed numbers that may be echoed back
    verbatim (warrant codes, tickers, numbers the user typed).
    """
    working = text.replace("\u202f", " ").replace("\u00a0", " ")

    for tok in sorted({t.strip() for t in (allowed_tokens or []) if t and t.strip()}, key=len, reverse=True):
        working = re.sub(rf"(?<![\w.]){re.escape(tok)}(?!\w)", " ", working, flags=re.IGNORECASE)

    offending: list[str] = []
    offending.extend(m.group(0).strip() for m in _FIGURE_PATTERN.finditer(working))
    offending.extend(m.group(0) for m in _NUMBER_WORD_PATTERN.finditer(working))
    offending.extend(m.group(0) for m in _PER_CENT_PATTERN.finditer(working))

    offending = [tok for tok in offending if tok]
    return NumberCheckResult(passed=not offending, offending_tokens=offending)
