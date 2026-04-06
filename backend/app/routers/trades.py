"""
Trade routes — trade history, execution, and summaries.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_mysql, get_mongo
from app.models.sql import Trade
from app.models.schemas import TradeResponse, TradeCreate, TradeSummary
from app.services.paper_trade import PaperTradeEngine
from app.config import settings

router = APIRouter(prefix="/api/trades", tags=["trades"])

# Default user ID for single-user staging mode
DEFAULT_USER = "default_user"


@router.get("/", response_model=list[TradeResponse])
async def list_trades(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    ticker: str | None = Query(default=None),
    action: str | None = Query(default=None, pattern="^(BUY|SELL)$"),
    status: str | None = Query(default=None, pattern="^(PENDING|FILLED|CANCELLED|REJECTED)$"),
    paper_only: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_mysql),
):
    """Get paginated trade history with optional filters."""
    query = select(Trade).where(Trade.user_id == DEFAULT_USER)

    if ticker:
        query = query.where(Trade.ticker == ticker.upper())
    if action:
        query = query.where(Trade.action == action)
    if status:
        query = query.where(Trade.status == status)
    if paper_only is not None:
        query = query.where(Trade.paper_flag == paper_only)

    query = query.order_by(desc(Trade.created_at))
    query = query.offset((page - 1) * limit).limit(limit)

    result = await db.execute(query)
    trades = result.scalars().all()
    return trades


@router.get("/summary/{ticker}", response_model=TradeSummary)
async def get_trade_summary(
    ticker: str,
    db: AsyncSession = Depends(get_mysql),
):
    """Get trade history summary for a ticker (for 'recurring' badge)."""
    query = (
        select(
            Trade.ticker,
            func.count().label("total_trades"),
            func.min(Trade.created_at).label("first_trade"),
            func.max(Trade.created_at).label("last_trade"),
            func.sum(
                func.IF(Trade.action == "BUY", Trade.quantity, 0)
            ).label("total_bought"),
            func.sum(
                func.IF(Trade.action == "SELL", Trade.quantity, 0)
            ).label("total_sold"),
        )
        .where(Trade.ticker == ticker.upper())
        .where(Trade.status == "FILLED")
        .group_by(Trade.ticker)
    )

    result = await db.execute(query)
    row = result.first()

    if row is None:
        return TradeSummary(
            ticker=ticker.upper(),
            total_trades=0,
            first_trade=None,
            last_trade=None,
            total_bought=0,
            total_sold=0,
        )

    return TradeSummary(
        ticker=row.ticker,
        total_trades=row.total_trades,
        first_trade=row.first_trade,
        last_trade=row.last_trade,
        total_bought=float(row.total_bought or 0),
        total_sold=float(row.total_sold or 0),
    )


@router.post("/", response_model=TradeResponse, status_code=201)
async def create_trade(
    trade: TradeCreate,
    db: AsyncSession = Depends(get_mysql),
    mongo=Depends(get_mongo),
):
    """
    Execute a new trade.
    In staging mode: uses the paper trading engine.
    In production mode: routes to IBKR (not yet implemented).
    """
    if not settings.paper_trade_enabled:
        raise HTTPException(
            status_code=501,
            detail="Live trading via IBKR not yet implemented"
        )

    engine = PaperTradeEngine(db=db, mongo=mongo)

    try:
        result = await engine.execute(
            user_id=DEFAULT_USER,
            ticker=trade.ticker,
            action=trade.action,
            quantity=trade.quantity,
            order_type=trade.order_type,
            target_price=trade.target_price,
            confidence=trade.confidence,
            reasoning=trade.reasoning,
            source_workflow=trade.source_workflow,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/recent", response_model=list[TradeResponse])
async def get_recent_trades(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_mysql),
):
    """Get the most recent trades for the dashboard widget."""
    query = (
        select(Trade)
        .where(Trade.user_id == DEFAULT_USER)
        .order_by(desc(Trade.created_at))
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()
