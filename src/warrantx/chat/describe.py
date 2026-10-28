"""Descriptor builder converting structured WarrantCard data into digit-free qualitative phrases.

The model prompt and plain-English outputs consume ONLY this descriptor; the numeric
WarrantCard payload is NEVER passed to the LLM or plain text answers.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from warrantx.config import load_flags
from warrantx.guardrails.templates import get_mode_phrase
from warrantx.chat.glossary import find_glossary_terms_in_text
from warrantx.tools.models import WarrantCard

FLAG_PHRASES: Dict[str, str] = {
    "SHORT_EXPIRY": "Approaching expiry with very few days remaining, so time decay is accelerating rapidly.",
    "WIDE_SPREAD": "Wide bid-ask spread creates elevated round-trip transaction drag when entering or exiting.",
    "LOW_LIQUIDITY": "Thin order book liquidity or absent bid quotes, increasing the risk of adverse slippage.",
    "DEEP_OTM": "Deep out-of-the-money warrant with negligible sensitivity to the underlying share price and elevated risk of expiring worthless.",
    "HIGH_DECAY": "Steep daily time decay eroding a large portion of the warrant price with each passing day.",
    "IV_RICH": "Implied volatility is rich compared to recent historical underlying swings, making the warrant expensive.",
    "ISSUER_MISMATCH": "Discrepancy detected between issuer-reported metrics and independently recomputed theoretical models.",
}


class ChatDescriptor(BaseModel):
    """Qualitative, digit-free summary of a warrant's profile and risks."""

    code: str
    ticker: str
    option_type: str
    phrases: List[str] = Field(default_factory=list)
    mode_phrase: str = ""
    glossary: List[str] = Field(default_factory=list)


def build_chat_descriptor(
    card: WarrantCard,
    mode: str = "sample",
    user_query: str = "",
) -> ChatDescriptor:
    """Build a qualitative ChatDescriptor strictly containing no figures or digits."""
    flags_cfg = load_flags()
    phrases: List[str] = []

    # 1. Map flagged risks to pure qualitative phrases
    for flag in card.flags:
        phrase = FLAG_PHRASES.get(flag.code)
        if phrase and phrase not in phrases:
            phrases.append(phrase)

    # 2. Qualitative gearing note
    high_gearing_thresh = float(flags_cfg.get("high_effective_gearing", 10.0))
    eg = card.metrics.effective_gearing if card.metrics else None
    if eg is not None:
        if eg >= high_gearing_thresh:
            phrases.append("Features high gearing, magnifying both potential gains and downside losses.")
        else:
            phrases.append("Moderate gearing exposure relative to the underlying share.")

    # 3. Moneyness qualitative assessment
    opt_type = (card.type or "call").lower()
    if card.underlying_price is not None and card.strike is not None and card.strike > 0:
        if "call" in opt_type:
            if card.underlying_price > card.strike:
                phrases.append("Currently in the money, holding intrinsic value.")
            else:
                phrases.append("Currently out of the money, relying entirely on future price appreciation.")
        elif "put" in opt_type:
            if card.underlying_price < card.strike:
                phrases.append("Currently in the money, holding intrinsic value.")
            else:
                phrases.append("Currently out of the money, relying entirely on future price depreciation.")

    # 4. Mode phrase
    mode_phrase = get_mode_phrase(card.mode or mode)

    # 5. Glossary terms matching user inquiry
    glossary = find_glossary_terms_in_text(user_query) if user_query else []

    return ChatDescriptor(
        code=card.code,
        ticker=card.underlying_ticker,
        option_type=card.type or "Call",
        phrases=phrases,
        mode_phrase=mode_phrase,
        glossary=glossary,
    )
