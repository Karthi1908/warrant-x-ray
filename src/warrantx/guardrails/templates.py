"""Standardized guardrail templates in English and Malay.

Includes:
- Mandatory educational disclaimers
- Explicit advice/prediction refusals
- Strip-and-note omission notices
- Degraded mode notices (budget exhausted, replay mode, sample mode)
"""

from __future__ import annotations

import re

# Malay indicator tokens for rapid language selection
_MALAY_TOKENS = {
    "saya", "anda", "beli", "jual", "waran", "harga", "naik", "turun",
    "boleh", "patut", "kah", "ini", "itu", "yang", "dan", "untuk",
    "berapa", "bila", "bagaimana", "kenapa", "adakah", "esok", "hari",
    "untung", "rugi", "saham", "pasaran"
}


def detect_language(text: str) -> str:
    """Heuristic language detector returning 'ms' for Malay and 'en' for English/other."""
    words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
    if not words:
        return "en"
    malay_count = sum(1 for w in words if w in _MALAY_TOKENS)
    return "ms" if (malay_count / len(words)) >= 0.20 or malay_count >= 3 else "en"


DISCLAIMERS = {
    "en": (
        "Educational and analytical tool only. Not financial, investment, or trading advice. "
        "Structured warrants are high-risk leveraged derivatives that can expire worthless."
    ),
    "ms": (
        "Alat pendidikan dan analitikal sahaja. Bukan nasihat kewangan, pelaburan, atau perdagangan. "
        "Waran berstruktur adalah derivatif berleveraj berisiko tinggi yang boleh luput tanpa nilai."
    ),
}

REFUSALS = {
    "en": (
        "I cannot provide investment advice, buy/sell recommendations, or future price predictions. "
        "I can show you factual warrant metrics, holding cost breakdowns, or simulate what-if scenarios "
        "based on your assumptions."
    ),
    "ms": (
        "Saya tidak dapat memberikan nasihat pelaburan, cadangan beli/jual, atau ramalan harga masa hadapan. "
        "Saya boleh menunjukkan metrik fakta waran, pecahan kos pemegangan, atau mensimulasikan senario "
        "'bagaimana jika' berdasarkan andaian anda."
    ),
}

OMISSION_NOTES = {
    "en": "[Note: Some unverified numbers or assertions were omitted for accuracy and compliance.]",
    "ms": "[Nota: Beberapa nombor atau pernyataan yang tidak dapat disahkan telah ditinggalkan untuk ketepatan dan kepatuhan.]",
}

BUDGET_EXHAUSTED_NOTICES = {
    "en": (
        "Daily AI compute budget has been reached. Providing factual data and cached market figures "
        "without model commentary."
    ),
    "ms": (
        "Had belanjawan komputasi AI harian telah dicapai. Menyediakan data fakta dan angka pasaran cache "
        "tanpa ulasan model."
    ),
}

REPLAY_NOTICES = {
    "en": "Operating in Replay mode using stored snapshot data. Live exchange market data is currently paused.",
    "ms": "Beroperasi dalam mod Replay menggunakan data snapshot yang disimpan. Data pasaran bursa langsung kini dijeda.",
}

SAMPLE_NOTICES = {
    "en": "Operating in Sample mode using synthetic data. Figures shown are illustrative and not real market quotes.",
    "ms": "Beroperasi dalam mod Sampel menggunakan data sintetik. Angka yang ditunjukkan adalah ilustrasi dan bukan sebut harga pasaran sebenar.",
}


def get_disclaimer(lang: str = "en") -> str:
    """Retrieve the standard educational disclaimer."""
    return DISCLAIMERS.get(lang.lower(), DISCLAIMERS["en"])


def get_refusal(lang: str = "en") -> str:
    """Retrieve the advice refusal message."""
    return REFUSALS.get(lang.lower(), REFUSALS["en"])


def get_omission_note(lang: str = "en") -> str:
    """Retrieve the strip-and-note omission warning."""
    return OMISSION_NOTES.get(lang.lower(), OMISSION_NOTES["en"])


def get_budget_exhausted_notice(lang: str = "en") -> str:
    """Retrieve the degraded budget notice."""
    return BUDGET_EXHAUSTED_NOTICES.get(lang.lower(), BUDGET_EXHAUSTED_NOTICES["en"])


def get_replay_notice(lang: str = "en") -> str:
    """Retrieve the replay mode notice."""
    return REPLAY_NOTICES.get(lang.lower(), REPLAY_NOTICES["en"])


def get_sample_notice(lang: str = "en") -> str:
    """Retrieve the sample data notice."""
    return SAMPLE_NOTICES.get(lang.lower(), SAMPLE_NOTICES["en"])


MODE_PHRASES = {
    "live": "Data is sourced from the live exchange market feed.",
    "replay": "Data is sourced from a historical market replay snapshot.",
    "sample": "Data is sourced from sample benchmark data.",
}

PLAIN_BUDGET_EXHAUSTED_NOTICES = {
    "en": (
        "The daily AI query limit has been reached. Factual warrant information and interactive "
        "links remain available below without model commentary."
    ),
    "ms": (
        "Had pertanyaan AI harian telah dicapai. Maklumat fakta waran dan pautan interaktif "
        "tetap tersedia di bawah tanpa ulasan model."
    ),
}


def get_mode_phrase(mode: str) -> str:
    """Retrieve digit-free mode description phrase."""
    return MODE_PHRASES.get(mode.lower(), MODE_PHRASES["sample"])


def get_plain_budget_notice(lang: str = "en") -> str:
    """Retrieve digit-free budget exhausted notice."""
    return PLAIN_BUDGET_EXHAUSTED_NOTICES.get(lang.lower(), PLAIN_BUDGET_EXHAUSTED_NOTICES["en"])


def get_plain_warrant_template(
    code: str,
    ticker: str,
    option_type: str,
    phrases: list[str],
    mode_phrase: str = "",
) -> str:
    """Deterministic, digit-free fallback summary for a warrant."""
    desc = f"This is a {option_type} warrant linked to {ticker} (code {code})."
    parts = [desc]
    if phrases:
        parts.extend(phrases)
    if mode_phrase:
        parts.append(mode_phrase)
    parts.append("Exact calculations, Greek metrics, and what-if scenarios are available via the links below.")
    return " ".join(parts)


def get_plain_term_template(term: str, explanation: str) -> str:
    """Deterministic, digit-free fallback explanation for a financial term."""
    return (
        f"Here is an overview of {term}: {explanation} "
        "Explore real-time calculations and live sensitivity through the links below."
    )


def get_plain_unknown_entity_template(query_snippet: str = "") -> str:
    """Deterministic, digit-free fallback when an entity is not found."""
    return (
        "The requested warrant or stock could not be identified in the active database. "
        "You can explore all available warrants by opening the stock screener below."
    )

