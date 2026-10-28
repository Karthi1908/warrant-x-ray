"""Static plain-English glossary for structured warrant concepts.

All definitions are strictly free of digits, percentages, currency amounts, and number words.
"""

from typing import Dict, List, Optional

GLOSSARY_DEFINITIONS: Dict[str, str] = {
    "gearing": (
        "Effective gearing measures how sharply the warrant price tends to move compared to "
        "movements in the underlying share. Higher gearing offers greater exposure, but losses "
        "also multiply if the share moves the wrong way."
    ),
    "spread": (
        "The bid-ask spread is the gap between the buying and selling prices quoted in the market. "
        "A narrower spread means lower trading friction when entering or exiting."
    ),
    "iv": (
        "Implied volatility reflects the market expectation of price swings in the underlying stock. "
        "Richer volatility makes warrants more expensive, while falling volatility deflates warrant "
        "prices even if the stock stays flat."
    ),
    "implied_volatility": (
        "Implied volatility reflects the market expectation of price swings in the underlying stock. "
        "Richer volatility makes warrants more expensive, while falling volatility deflates warrant "
        "prices even if the stock stays flat."
    ),
    "theta": (
        "Time decay reflects the steady loss in warrant value as the final expiry date approaches. "
        "Warrants lose value faster as they near the end of their lifespan, meaning holding them "
        "over time incurs a daily drag."
    ),
    "time_decay": (
        "Time decay reflects the steady loss in warrant value as the final expiry date approaches. "
        "Warrants lose value faster as they near the end of their lifespan, meaning holding them "
        "over time incurs a daily drag."
    ),
    "delta": (
        "Delta indicates the sensitivity of the warrant price to a change in the underlying stock price. "
        "For a call warrant, delta is positive, meaning the warrant gains value when the underlying rises."
    ),
    "breakeven": (
        "Break-even represents the level the underlying share must reach at expiry for the warrant holder "
        "to cover the total purchase cost. Beyond that point, the position enters net profit."
    ),
    "break_even": (
        "Break-even represents the level the underlying share must reach at expiry for the warrant holder "
        "to cover the total purchase cost. Beyond that point, the position enters net profit."
    ),
    "moneyness": (
        "Moneyness describes where the underlying share price sits relative to the strike price. "
        "An in-the-money warrant already holds intrinsic value, whereas an out-of-the-money warrant "
        "carries only speculative time value."
    ),
    "expiry": (
        "Expiry is the predetermined date when the warrant reaches the end of its life. After this final "
        "cutoff, warrants cease trading and any remaining value is settled or lost."
    ),
}

# Lookup aliases mapping variations/subwords to canonical keys
TERM_ALIASES: Dict[str, str] = {
    "gearing": "gearing",
    "effective gearing": "gearing",
    "leverage": "gearing",
    "spread": "spread",
    "bid-ask": "spread",
    "bid ask": "spread",
    "iv": "iv",
    "implied volatility": "iv",
    "volatility": "iv",
    "theta": "theta",
    "time decay": "theta",
    "decay": "theta",
    "holding cost": "theta",
    "delta": "delta",
    "sensitivity": "delta",
    "breakeven": "breakeven",
    "break-even": "breakeven",
    "break even": "breakeven",
    "moneyness": "moneyness",
    "itm": "moneyness",
    "otm": "moneyness",
    "in the money": "moneyness",
    "out of the money": "moneyness",
    "expiry": "expiry",
    "expiration": "expiry",
    "maturity": "expiry",
}


def get_glossary_term(term: str) -> Optional[str]:
    """Retrieve explanation for a single term, normalizing case and aliases."""
    normalized = term.strip().lower()
    canonical = TERM_ALIASES.get(normalized, normalized)
    return GLOSSARY_DEFINITIONS.get(canonical)


def find_glossary_terms_in_text(text: str) -> List[str]:
    """Find relevant glossary explanations for terms mentioned in the user message."""
    lowered = text.lower()
    explanations: List[str] = []
    seen_canonical = set()

    for alias, canonical in TERM_ALIASES.items():
        if alias in lowered and canonical not in seen_canonical:
            seen_canonical.add(canonical)
            exp = GLOSSARY_DEFINITIONS.get(canonical)
            if exp:
                explanations.append(exp)

    return explanations
