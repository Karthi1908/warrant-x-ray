"""Unit tests for Bursa Malaysia warrant ratio convention selection (T032).

Covers:
- Standard Bursa Malaysia convention: ratio R represents R warrants per 1 underlying share
- Verification that shares_per_warrant = 1.0 / ratio
- Handling of edge cases (fractional ratio, integer ratio, invalid ratio)
"""

import math
import pytest
from warrantx.quant.ratio import parse_ratio_convention, shares_per_warrant


def test_standard_bursa_ratio() -> None:
    """Standard ratio: 4.0 means 4 warrants : 1 share -> 0.25 shares per warrant."""
    conv = parse_ratio_convention(4.0)
    assert conv.warrants_per_share == 4.0
    assert math.isclose(conv.shares_per_warrant, 0.25, rel_tol=1e-6)


def test_varied_ratios() -> None:
    """Ratios like 1.0, 2.5, 5.0, 10.0."""
    cases = [(1.0, 1.0), (2.0, 0.50), (2.5, 0.40), (5.0, 0.20), (10.0, 0.10)]
    for raw_ratio, expected_shares in cases:
        spw = shares_per_warrant(raw_ratio)
        assert math.isclose(spw, expected_shares, rel_tol=1e-6)


def test_invalid_ratio() -> None:
    """Non-positive ratio raises ValueError."""
    with pytest.raises(ValueError, match="Ratio must be positive"):
        parse_ratio_convention(0.0)
    with pytest.raises(ValueError, match="Ratio must be positive"):
        parse_ratio_convention(-4.0)
