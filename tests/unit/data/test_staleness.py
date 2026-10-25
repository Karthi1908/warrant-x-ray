"""Unit tests for market session hours, staleness classification, and data mode (T073, FR-DATA-07, FR-ERR-02 to 04).

Tests:
1. Market hours staleness: >20 minutes during trading hours is stale.
2. Market hours freshness: <=20 minutes during trading hours is fresh.
3. Market closed: evening, weekend, lunch break (12:30-14:30), or exchange holiday is market_closed, not stale.
4. Sample mode: active when no live snapshots are loaded.
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pytest

from warrantx.data.staleness import (
    is_bursa_trading_day,
    is_market_open,
    evaluate_data_staleness,
)

KL_TZ = ZoneInfo("Asia/Kuala_Lumpur")


def test_bursa_market_hours_open():
    """Bursa is open 09:00-12:30 and 14:30-17:00 MYT on non-holiday weekdays."""
    # Wednesday 10:30 AM MYT
    dt_morning = datetime(2026, 10, 14, 10, 30, tzinfo=KL_TZ)
    assert is_bursa_trading_day(dt_morning.date()) is True
    assert is_market_open(dt_morning) is True

    # Wednesday 15:30 PM MYT
    dt_afternoon = datetime(2026, 10, 14, 15, 30, tzinfo=KL_TZ)
    assert is_market_open(dt_afternoon) is True


def test_bursa_market_hours_closed():
    """Bursa is closed during lunch break, evening, weekends, and holidays."""
    # Lunch break 13:00 MYT
    dt_lunch = datetime(2026, 10, 14, 13, 0, tzinfo=KL_TZ)
    assert is_market_open(dt_lunch) is False

    # Evening 18:00 MYT
    dt_evening = datetime(2026, 10, 14, 18, 0, tzinfo=KL_TZ)
    assert is_market_open(dt_evening) is False

    # Weekend (Sunday 11:00 MYT)
    dt_sunday = datetime(2026, 10, 18, 11, 0, tzinfo=KL_TZ)
    assert is_bursa_trading_day(dt_sunday.date()) is False
    assert is_market_open(dt_sunday) is False


def test_staleness_during_market_hours():
    """During open market, data older than 20 minutes is flagged stale."""
    now_open = datetime(2026, 10, 14, 10, 30, tzinfo=KL_TZ)

    # 10 minutes old -> fresh
    fetched_10m = datetime(2026, 10, 14, 10, 20, tzinfo=KL_TZ)
    res_fresh = evaluate_data_staleness(fetched_at=fetched_10m, now=now_open, has_live_feed=True)
    assert res_fresh.is_stale is False
    assert res_fresh.market_open is True
    assert res_fresh.mode == "live"

    # 25 minutes old -> stale
    fetched_25m = datetime(2026, 10, 14, 10, 5, tzinfo=KL_TZ)
    res_stale = evaluate_data_staleness(fetched_at=fetched_25m, now=now_open, has_live_feed=True)
    assert res_stale.is_stale is True
    assert res_stale.market_open is True


def test_staleness_outside_market_hours():
    """Outside market hours, old data is NOT stale; market is simply closed."""
    now_closed = datetime(2026, 10, 14, 20, 0, tzinfo=KL_TZ)
    fetched_earlier = datetime(2026, 10, 14, 16, 55, tzinfo=KL_TZ)

    res = evaluate_data_staleness(fetched_at=fetched_earlier, now=now_closed, has_live_feed=True)
    assert res.is_stale is False
    assert res.market_open is False
    assert res.status == "market_closed"


def test_sample_mode_when_no_feed():
    """When no live feed has ever run, data mode defaults to 'sample'."""
    now = datetime(2026, 10, 14, 10, 30, tzinfo=KL_TZ)
    res = evaluate_data_staleness(fetched_at=None, now=now, has_live_feed=False)
    assert res.mode == "sample"
