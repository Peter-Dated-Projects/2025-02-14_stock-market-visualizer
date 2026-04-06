"""
Market data routes — proxies to Polygon.io with Redis caching.
"""

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import TickerSnapshot, AggregateBar, TickerDetails
from app.services import polygon

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/snapshot/{ticker}", response_model=TickerSnapshot)
async def get_snapshot(ticker: str):
    """
    Get current snapshot for a ticker: price, bid/ask, volume, day change.
    Cached for 5 minutes.
    """
    data = await polygon.get_snapshot(ticker)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker.upper()} not found")
    return data


@router.get("/aggregates/{ticker}", response_model=list[AggregateBar])
async def get_aggregates(
    ticker: str,
    multiplier: int = Query(default=1, ge=1, le=60),
    timespan: str = Query(default="day", pattern="^(minute|hour|day|week|month)$"),
    date_from: str | None = Query(default=None, description="YYYY-MM-DD"),
    date_to: str | None = Query(default=None, description="YYYY-MM-DD"),
    limit: int = Query(default=120, ge=1, le=5000),
):
    """
    Get OHLCV aggregate bars for charting.
    Timespan: minute, hour, day, week, month.
    Cached for 24 hours.
    """
    data = await polygon.get_aggregates(
        ticker=ticker,
        multiplier=multiplier,
        timespan=timespan,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    if data is None:
        raise HTTPException(status_code=404, detail=f"No aggregate data for {ticker.upper()}")
    return data


@router.get("/details/{ticker}", response_model=TickerDetails)
async def get_ticker_details(ticker: str):
    """
    Get company details: name, description, industry, market cap.
    Cached for 7 days.
    """
    data = await polygon.get_ticker_details(ticker)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker.upper()} not found")
    return data


@router.get("/batch-snapshot")
async def get_batch_snapshots(
    tickers: str = Query(..., description="Comma-separated ticker symbols, e.g. AAPL,NVDA,MSFT"),
):
    """
    Get snapshots for multiple tickers in one request.
    Returns {ticker: snapshot}.
    """
    ticker_list = [t.strip() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        raise HTTPException(status_code=400, detail="No tickers provided")
    if len(ticker_list) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 tickers per request")

    data = await polygon.get_batch_snapshots(ticker_list)
    return {"tickers": data}
