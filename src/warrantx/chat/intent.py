"""Intent classification combining rules-first entity extraction with Nano JSON parsing.

Conforms to specs/002-local-chat/data-model.md.
"""

from __future__ import annotations

import re
from typing import Any, Literal, Optional, Sequence
from pydantic import BaseModel

from warrantx.chat.glossary import TERM_ALIASES
from warrantx.data.repo import AsyncRepository
from warrantx.llm.direct import direct_nano_json_call

IntentType = Literal["explain_warrant", "explain_term", "compare", "news", "scenario", "other"]

LEGAL_SUFFIXES = re.compile(
    r"\b(bhd|berhad|group|grp|holdings|holding|hldgs|hldngs|corporation|corp|"
    r"inc|intl|international|limited|ltd|sdn\s+bhd|sdn|co\.?|\(m\)|reit|ord|tech|techno|chnlgy)\b",
    re.IGNORECASE,
)

KNOWN_UNDERLYING_ALIASES: dict[str, str] = {
    # Banking
    "rhb": "RHBBANK",
    "rhb bank": "RHBBANK",
    "rhbbank": "RHBBANK",
    "public bank": "PBBANK",
    "public bank berhad": "PBBANK",
    "public bank bhd": "PBBANK",
    "pbbank": "PBBANK",
    "pbb": "PBBANK",
    "hong leong": "HLBANK",
    "hong leong bank": "HLBANK",
    "hlbank": "HLBANK",
    "hlb": "HLBANK",
    "hlfg": "HLFG",
    "maybank": "MAYBANK",
    "may bank": "MAYBANK",
    "mbb": "MAYBANK",
    "cimb": "CIMB",
    "cimb bank": "CIMB",
    "cimb group": "CIMB",
    "ambank": "AMBANK",
    "am bank": "AMBANK",
    "ammb": "AMBANK",
    "alliance bank": "ABMB",
    "abmb": "ABMB",
    "affin": "AFFIN",
    "affin bank": "AFFIN",
    "mbsb": "MBSB",
    # Utilities, Conglomerates & Key stocks
    "tnb": "TENAGA",
    "tenaga": "TENAGA",
    "tenaga nasional": "TENAGA",
    "tenaga nasional berhad": "TENAGA",
    "ytl power": "YTLPOWR",
    "ytlpower": "YTLPOWR",
    "ytl corp": "YTL",
    "ytl corporation": "YTL",
    "ytl": "YTL",
    "top glove": "TOPGLOV",
    "topglove": "TOPGLOV",
    "hartalega": "HARTA",
    "kossan": "KOSSAN",
    "supermax": "SUPERMAX",
    "press metal": "PMETAL",
    "press metal aluminium": "PMETAL",
    "pmetal": "PMETAL",
    "petronas chemicals": "PCHEM",
    "petronas chemical": "PCHEM",
    "petchem": "PCHEM",
    "pchem": "PCHEM",
    "petronas gas": "PETGAS",
    "petgas": "PETGAS",
    "petronas dagangan": "PETDAG",
    "petdag": "PETDAG",
    "petronas": "PETGAS",
    "sime darby": "SIME",
    "sime": "SIME",
    "sime darby property": "SIMEPROP",
    "simeprop": "SIMEPROP",
    "sime darby plantation": "SIMEPLT",
    "sime plantation": "SIMEPLT",
    "sd guthrie": "SIMEPLT",
    "guthrie": "SIMEPLT",
    "genting": "GENTING",
    "genting malaysia": "GENM",
    "genm": "GENM",
    "genting plantations": "GENP",
    "genp": "GENP",
    "celcom": "CELCOMDIGI",
    "digi": "CELCOMDIGI",
    "celcomdigi": "CELCOMDIGI",
    "telekom": "TM",
    "telekom malaysia": "TM",
    "airasia": "AIRASIA",
    "capital a": "CAPITALA",
    "mr diy": "MRDIY",
    "mrdiy": "MRDIY",
    "mr d.i.y.": "MRDIY",
    "mr d.i.y": "MRDIY",
    "gamuda": "GAMUDA",
    "bursa": "BURSA",
    "bursa malaysia": "BURSA",
    "myeg": "MYEG",
    "my eg": "MYEG",
    "maxis": "MAXIS",
    "misc": "MISC",
    "ihh": "IHH",
    "ihh healthcare": "IHH",
    "inari": "INARI",
    "sunway": "SUNWAY",
    "suncon": "SUNCON",
    "ecoworld": "ECOWLD",
    "eco world": "ECOWLD",
    "sp setia": "SPSETIA",
    "klk": "KLK",
    "kuala lumpur kepong": "KLK",
    "ioicorp": "IOICORP",
    "ioi corp": "IOICORP",
    "ioi properties": "IOIPG",
    "drb hicom": "DRBHCOM",
    "drb-hicom": "DRBHCOM",
    "dialog": "DIALOG",
    "dialog group": "DIALOG",
    "hibiscus": "HIBISCS",
    "hibiscus petroleum": "HIBISCS",
    "frontken": "FRONTKN",
    "greatech": "GREATEC",
    "vitrox": "VITROX",
    "dnex": "DNEX",
    "dagang nexchange": "DNEX",
}


def clean_company_name(name: str) -> str:
    """Normalize company name by removing corporate legal designations."""
    cleaned = LEGAL_SUFFIXES.sub(" ", name.lower())
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _extract_ticker_name(u: Any) -> tuple[str, str]:
    if hasattr(u, "ticker"):
        return str(u.ticker or ""), str(getattr(u, "name", "") or "")
    if isinstance(u, (tuple, list)) and len(u) >= 2:
        return str(u[0] or ""), str(u[1] or "")
    if isinstance(u, dict):
        return str(u.get("ticker", "") or ""), str(u.get("name", "") or "")
    return str(u), ""


def resolve_underlying_ticker(message: str, underlyings: Sequence[Any]) -> Optional[str]:
    """Resolve user query to an underlying stock ticker using aliases, boundaries, and normalized company names."""
    lowered = message.lower()

    # 1. Check known aliases (longest first for maximum specificity)
    for alias in sorted(KNOWN_UNDERLYING_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", lowered):
            return KNOWN_UNDERLYING_ALIASES[alias]

    items = [_extract_ticker_name(u) for u in underlyings]

    # 2. Exact ticker match (case-insensitive for len >= 3; exact-case boundary for <= 2)
    for ticker, _ in items:
        t_clean = ticker.strip()
        if len(t_clean) >= 3:
            if re.search(rf"\b{re.escape(t_clean.lower())}\b", lowered):
                return ticker
        elif len(t_clean) <= 2:
            if re.search(rf"\b{re.escape(t_clean)}\b", message):
                return ticker

    # 3. Cleaned company names (sorted by length descending)
    cleaned_names = []
    for ticker, name in items:
        if name:
            c = clean_company_name(name)
            if len(c) >= 3:
                cleaned_names.append((c, ticker))
    cleaned_names.sort(key=lambda x: len(x[0]), reverse=True)

    for c, ticker in cleaned_names:
        if re.search(rf"\b{re.escape(c)}\b", lowered):
            return ticker

    # 4. Bank and corporate stem variations (e.g. RHBBANK -> stem RHB)
    for ticker, _ in items:
        if ticker.upper().endswith("BANK") and len(ticker) > 4:
            stem = ticker[:-4].lower()
            if len(stem) >= 3:
                if re.search(rf"\b{re.escape(stem)}(\s+bank)?\b", lowered):
                    return ticker

    return None


class ParsedIntent(BaseModel):
    """Normalized intent and entity targets."""

    intent: IntentType = "other"
    code: Optional[str] = None
    ticker: Optional[str] = None
    term: Optional[str] = None


async def classify_intent(
    message: str,
    repo: AsyncRepository,
    use_model: bool = False,
) -> ParsedIntent:
    """Classify user intent using rules-first heuristics, falling back to Nano JSON if needed."""
    lowered = message.lower()
    code: Optional[str] = None
    ticker: Optional[str] = None
    term: Optional[str] = None
    intent: IntentType = "other"

    # 1. Identify warrant code via regex and repo lookup
    tokens = re.findall(r"\b[A-Za-z0-9]{4,8}\b", message)
    for tok in tokens:
        cand = tok.upper()
        row = await repo.get_warrant(cand)
        if row:
            code = cand
            ticker = row.underlying_ticker
            break

    # 2. Identify underlying ticker
    if not ticker:
        underlyings = await repo.list_underlyings()
        ticker = resolve_underlying_ticker(message, underlyings)

    # 3. Identify financial term
    for alias in TERM_ALIASES:
        if re.search(rf"\b{re.escape(alias)}\b", lowered):
            term = TERM_ALIASES[alias]
            break

    # 4. Rules heuristic classification
    if any(k in lowered for k in ["news", "headline", "article", "berita", "artikel"]):
        intent = "news"
    elif any(k in lowered for k in ["compare", "vs", "versus", "bandingkan", "banding"]):
        intent = "compare"
    elif any(k in lowered for k in ["scenario", "what if", "what-if", "simulate", "simulation", "simulasi"]):
        intent = "scenario"
    elif code:
        intent = "explain_warrant"
    elif term and not ticker:
        intent = "explain_term"
    elif ticker:
        intent = "explain_warrant"
    else:
        intent = "other"

    # 5. Nano JSON fallback when intent is unresolved and use_model is True
    if intent == "other" and use_model:
        prompt = (
            f"Classify the warrant query: '{message}'. "
            "Return JSON matching: {\"intent\": \"explain_warrant|explain_term|compare|news|scenario|other\", "
            "\"code\": string|null, \"ticker\": string|null, \"term\": string|null}"
        )
        try:
            parsed = await direct_nano_json_call(prompt=prompt, response_model=ParsedIntent)
            if isinstance(parsed, ParsedIntent):
                return parsed
        except Exception:
            pass

    return ParsedIntent(intent=intent, code=code, ticker=ticker, term=term)
