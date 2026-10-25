"""Bursa Malaysia trading calendar, market session hours, and data staleness evaluation.

Implements FR-DATA-07, FR-ERR-02 to FR-ERR-04:
- Trading days: Monday to Friday, excluding official exchange holidays.
- Trading hours: 09:00 - 12:30 MYT (Morning Session) and 14:30 - 17:00 MYT (Afternoon Session).
- Outside market hours (lunch, evenings, weekends, holidays), data is not stale;
  status is 'market_closed'.
- When no live feed has run, mode is 'sample'.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

KL_TZ = ZoneInfo("Asia/Kuala_Lumpur")

# Morning session: 09:00 to 12:30
MORNING_OPEN = time(9, 0, 0)
MORNING_CLOSE = time(12, 30, 0)

# Afternoon session: 14:30 to 17:00
AFTERNOON_OPEN = time(14, 30, 0)
AFTERNOON_CLOSE = time(17, 0, 0)

STALENESS_THRESHOLD_SECONDS = 20 * 60  # 20 minutes


def _load_holidays() -> set[str]:
    """Load exchange holidays from config/bursa_holidays.yaml."""
    holidays: set[str] = set()
    holiday_file = Path("config/bursa_holidays.yaml")
    if holiday_file.exists():
        try:
            with open(holiday_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data and "calendar" in data:
                for year, events in data["calendar"].items():
                    if isinstance(events, list):
                        for event in events:
                            if isinstance(event, dict) and "date" in event:
                                holidays.add(str(event["date"]).strip())
        except Exception:
            pass
    return holidays


BURSA_HOLIDAYS = _load_holidays()


def is_bursa_trading_day(d: date) -> bool:
    """Check if date is a Bursa Malaysia trading day (weekday and non-holiday)."""
    # 5 is Saturday, 6 is Sunday
    if d.weekday() >= 5:
        return False
    date_str = d.isoformat()
    if date_str in BURSA_HOLIDAYS:
        return False
    return True


def is_market_open(dt: datetime) -> bool:
    """Check if Bursa Malaysia market is currently open for trading."""
    dt_kl = dt.astimezone(KL_TZ)
    if not is_bursa_trading_day(dt_kl.date()):
        return False

    t = dt_kl.time()
    if MORNING_OPEN <= t < MORNING_CLOSE:
        return True
    if AFTERNOON_OPEN <= t < AFTERNOON_CLOSE:
        return True
    return False


@dataclass
class StalenessResult:
    """Evaluation result for data staleness and session state."""

    is_stale: bool
    market_open: bool
    mode: str  # "live" | "sample" | "replay"
    status: str  # "fresh" | "stale" | "market_closed" | "sample"
    staleness_seconds: int = 0
    as_of: str | None = None


def evaluate_data_staleness(
    fetched_at: datetime | str | None,
    now: datetime | None = None,
    has_live_feed: bool = True,
    default_mode: str = "live",
) -> StalenessResult:
    """Evaluate whether warrant market data is fresh, stale, or market is closed."""
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    now_kl = now.astimezone(KL_TZ)
    market_is_open = is_market_open(now_kl)

    if not has_live_feed or fetched_at is None:
        return StalenessResult(
            is_stale=False,
            market_open=market_is_open,
            mode="sample",
            status="sample",
            staleness_seconds=0,
            as_of=None,
        )

    if isinstance(fetched_at, str):
        try:
            fetched_at_dt = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        except ValueError:
            fetched_at_dt = now
    else:
        fetched_at_dt = fetched_at

    if fetched_at_dt.tzinfo is None:
        fetched_at_dt = fetched_at_dt.replace(tzinfo=timezone.utc)

    age_seconds = max(0, int((now - fetched_at_dt).total_seconds()))

    if not market_is_open:
        return StalenessResult(
            is_stale=False,
            market_open=False,
            mode=default_mode,
            status="market_closed",
            staleness_seconds=age_seconds,
            as_of=fetched_at_dt.isoformat(),
        )

    # Market is open
    is_stale = age_seconds > STALENESS_THRESHOLD_SECONDS
    status = "stale" if is_stale else "fresh"

    return StalenessResult(
        is_stale=is_stale,
        market_open=True,
        mode=default_mode,
        status=status,
        staleness_seconds=age_seconds,
        as_of=fetched_at_dt.isoformat(),
    )
