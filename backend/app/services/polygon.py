"""
Polygon.io API client.

Handles all communication with the Polygon REST API, including:
- Ticker snapshots (current price, bid/ask, volume)
- Aggregate bars (OHLCV) for charting
- Ticker details (company info)

All responses are cached in Redis with appropriate TTLs.
Free tier: 5 requests/minute — we use aggressive caching to stay within limits.
"""

import logging
from datetime import datetime, timedelta

import httpx

from app.config import settings
from app.services.cache import (
    TTL_SNAPSHOT,
    TTL_AGGREGATES,
    TTL_HISTORY,
    cache_get_or_fetch,
    key_snapshot,
    key_aggregates,
    key_history,
)

logger = logging.getLogger("smv.polygon")

# Shared async HTTP client — reused across requests
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """Lazy-init the HTTP client."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=settings.polygon_base_url,
            timeout=15.0,
            headers={"Accept": "application/json"},
        )
    return _client


async def close_client() -> None:
    """Close the HTTP client. Called on app shutdown."""
    global _client
    if _client:
        await _client.aclose()
        _client = None


# ──────────────────────────────────────────────
# API Helpers
# ──────────────────────────────────────────────

async def _request(path: str, params: dict | None = None) -> dict | None:
    """
    Make an authenticated GET request to Polygon.
    Returns parsed JSON or None on error.
    """
    client = _get_client()
    all_params = {"apiKey": settings.polygon_api_key}
    if params:
        all_params.update(params)

    try:
        resp = await client.get(path, params=all_params)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Polygon API {e.response.status_code}: {path} — {e.response.text[:200]}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Polygon request failed: {path} — {e}")
        return None


# ──────────────────────────────────────────────
# Ticker Snapshot
# ──────────────────────────────────────────────

async def get_snapshot(ticker: str) -> dict | None:
    """
    Get current ticker snapshot: price, bid, ask, volume, day change.
    Cached for 5 minutes.

    Response shape:
    {
        "ticker": "NVDA",
        "price": 892.34,
        "bid": 892.10,
        "ask": 892.58,
        "volume": 42150000,
        "change": 12.50,
        "change_percent": 1.42,
        "prev_close": 879.84,
        "open": 881.00,
        "high": 895.00,
        "low": 878.50,
        "timestamp": "2024-01-15T16:00:00Z"
    }
    """
    cache_key = key_snapshot(ticker)

    async def fetch():
        data = await _request(f"/v2/snapshot/locale/us/markets/stocks/tickers/{ticker.upper()}")
        if not data or data.get("status") != "OK":
            return None

        t = data.get("ticker", {})
        day = t.get("day", {})
        prev_day = t.get("prevDay", {})
        last_quote = t.get("lastQuote", {})
        last_trade = t.get("lastTrade", {})

        return {
            "ticker": ticker.upper(),
            "price": last_trade.get("p", 0),
            "bid": last_quote.get("p", 0),
            "ask": last_quote.get("P", 0),
            "volume": day.get("v", 0),
            "change": t.get("todaysChange", 0),
            "change_percent": t.get("todaysChangePerc", 0),
            "prev_close": prev_day.get("c", 0),
            "open": day.get("o", 0),
            "high": day.get("h", 0),
            "low": day.get("l", 0),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    return await cache_get_or_fetch(cache_key, TTL_SNAPSHOT, fetch)


# ──────────────────────────────────────────────
# Aggregate Bars (OHLCV)
# ──────────────────────────────────────────────

async def get_aggregates(
    ticker: str,
    multiplier: int = 1,
    timespan: str = "day",
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 120,
) -> list[dict] | None:
    """
    Get OHLCV bars for a ticker.

    timespan: minute, hour, day, week, month
    Returns list of:
    {
        "open": 881.00,
        "high": 895.00,
        "low": 878.50,
        "close": 892.34,
        "volume": 42150000,
        "timestamp": "2024-01-15",
        "vwap": 886.50,
        "transactions": 250000
    }
    """
    if date_to is None:
        date_to = datetime.utcnow().strftime("%Y-%m-%d")
    if date_from is None:
        # Default lookback based on timespan
        lookback = {
            "minute": timedelta(days=1),
            "hour": timedelta(days=7),
            "day": timedelta(days=120),
            "week": timedelta(days=365),
            "month": timedelta(days=730),
        }.get(timespan, timedelta(days=120))
        date_from = (datetime.utcnow() - lookback).strftime("%Y-%m-%d")

    cache_key = key_aggregates(ticker, f"{multiplier}{timespan}", date_from, date_to)

    async def fetch():
        path = f"/v2/aggs/ticker/{ticker.upper()}/range/{multiplier}/{timespan}/{date_from}/{date_to}"
        data = await _request(path, {"adjusted": "true", "sort": "asc", "limit": str(limit)})

        if not data or data.get("resultsCount", 0) == 0:
            return None

        results = data.get("results", [])
        return [
            {
                "open": bar.get("o"),
                "high": bar.get("h"),
                "low": bar.get("l"),
                "close": bar.get("c"),
                "volume": bar.get("v"),
                "vwap": bar.get("vw"),
                "transactions": bar.get("n"),
                "timestamp": datetime.utcfromtimestamp(bar["t"] / 1000).strftime("%Y-%m-%d %H:%M:%S")
                if "t" in bar else None,
            }
            for bar in results
        ]

    return await cache_get_or_fetch(cache_key, TTL_AGGREGATES, fetch)


# ──────────────────────────────────────────────
# Batch Snapshots (for multiple tickers)
# ──────────────────────────────────────────────

async def get_batch_snapshots(tickers: list[str]) -> dict[str, dict]:
    """
    Get snapshots for multiple tickers at once.
    Uses the all-tickers endpoint and filters, reducing API calls.
    Returns {ticker: snapshot_data}
    """
    # For small lists, fetch individually (uses cache per ticker)
    if len(tickers) <= 3:
        results = {}
        for ticker in tickers:
            snap = await get_snapshot(ticker)
            if snap:
                results[ticker.upper()] = snap
        return results

    # For larger lists, use the batch endpoint
    ticker_str = ",".join(t.upper() for t in tickers)
    data = await _request(
        "/v2/snapshot/locale/us/markets/stocks/tickers",
        {"tickers": ticker_str},
    )

    if not data or data.get("status") != "OK":
        return {}

    results = {}
    for t in data.get("tickers", []):
        ticker_name = t.get("ticker", "")
        day = t.get("day", {})
        prev_day = t.get("prevDay", {})
        last_quote = t.get("lastQuote", {})
        last_trade = t.get("lastTrade", {})

        results[ticker_name] = {
            "ticker": ticker_name,
            "price": last_trade.get("p", 0),
            "bid": last_quote.get("p", 0),
            "ask": last_quote.get("P", 0),
            "volume": day.get("v", 0),
            "change": t.get("todaysChange", 0),
            "change_percent": t.get("todaysChangePerc", 0),
            "prev_close": prev_day.get("c", 0),
            "open": day.get("o", 0),
            "high": day.get("h", 0),
            "low": day.get("l", 0),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    return results


# ──────────────────────────────────────────────
# Ticker Details
# ──────────────────────────────────────────────

async def get_ticker_details(ticker: str) -> dict | None:
    """
    Get company details: name, description, industry, market cap, etc.
    Cached for 7 days (rarely changes).
    """
    cache_key = key_history(ticker, "details")

    async def fetch():
        data = await _request(f"/v3/reference/tickers/{ticker.upper()}")
        if not data or data.get("status") != "OK":
            return None

        r = data.get("results", {})
        return {
            "ticker": r.get("ticker"),
            "name": r.get("name"),
            "description": r.get("description", ""),
            "industry": r.get("sic_description", ""),
            "market_cap": r.get("market_cap"),
            "homepage": r.get("homepage_url"),
            "locale": r.get("locale"),
            "type": r.get("type"),
        }

    return await cache_get_or_fetch(cache_key, TTL_HISTORY, fetch)
