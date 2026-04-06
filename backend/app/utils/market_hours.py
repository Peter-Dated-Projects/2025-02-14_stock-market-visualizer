"""
NYSE market hours helpers.

Used by agent workflows to determine if they should run
(most workflows only execute during market hours).
"""

from datetime import datetime, time
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# NYSE regular trading hours
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)

# NYSE holidays 2024-2025 (extend as needed)
NYSE_HOLIDAYS = {
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29",
    "2024-05-27", "2024-06-19", "2024-07-04", "2024-09-02",
    "2024-11-28", "2024-12-25",
    "2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18",
    "2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01",
    "2025-11-27", "2025-12-25",
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03",
    "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07",
    "2026-11-26", "2026-12-25",
}


def now_et() -> datetime:
    """Get current time in Eastern Time."""
    return datetime.now(ET)


def is_market_open() -> bool:
    """Check if NYSE is currently in regular trading hours."""
    now = now_et()

    # Weekend check
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False

    # Holiday check
    if now.strftime("%Y-%m-%d") in NYSE_HOLIDAYS:
        return False

    # Hours check
    current_time = now.time()
    return MARKET_OPEN <= current_time <= MARKET_CLOSE


def is_trading_day() -> bool:
    """Check if today is a trading day (weekday + not a holiday)."""
    now = now_et()
    if now.weekday() >= 5:
        return False
    return now.strftime("%Y-%m-%d") not in NYSE_HOLIDAYS


def minutes_until_open() -> int | None:
    """Minutes until market opens. Returns None if market is open."""
    if is_market_open():
        return None
    now = now_et()
    open_dt = now.replace(hour=9, minute=30, second=0, microsecond=0)
    if now.time() > MARKET_CLOSE:
        # After close — next open is tomorrow (skip weekends)
        open_dt = open_dt.replace(day=now.day + 1)
        while open_dt.weekday() >= 5 or open_dt.strftime("%Y-%m-%d") in NYSE_HOLIDAYS:
            open_dt = open_dt.replace(day=open_dt.day + 1)
    diff = (open_dt - now).total_seconds()
    return max(0, int(diff / 60))


def minutes_until_close() -> int | None:
    """Minutes until market closes. Returns None if market is closed."""
    if not is_market_open():
        return None
    now = now_et()
    close_dt = now.replace(hour=16, minute=0, second=0, microsecond=0)
    diff = (close_dt - now).total_seconds()
    return max(0, int(diff / 60))
