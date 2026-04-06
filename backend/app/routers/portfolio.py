"""
Portfolio routes — holdings, performance, industries, stocks of interest.
All data comes from MongoDB.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_mongo
from app.models.schemas import (
    PortfolioResponse,
    IndustrySentiment,
    StockOfInterest,
)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

DEFAULT_USER = "default_user"


@router.get("/", response_model=PortfolioResponse)
async def get_portfolio(mongo=Depends(get_mongo)):
    """Get current portfolio: cash balance, holdings, total value."""
    portfolio = await mongo.portfolios.find_one({"user_id": DEFAULT_USER})
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    return PortfolioResponse(
        user_id=portfolio["user_id"],
        cash_balance=portfolio.get("cash_balance", 0),
        holdings=portfolio.get("holdings", []),
        looking_at_industries=portfolio.get("looking_at_industries", []),
        avoiding_industries=portfolio.get("avoiding_industries", []),
        stocks_of_interest=portfolio.get("stocks_of_interest", []),
        updated_at=portfolio.get("updated_at"),
    )


@router.get("/industries")
async def get_industries(mongo=Depends(get_mongo)):
    """Get looking-at and avoiding industry sentiments."""
    portfolio = await mongo.portfolios.find_one({"user_id": DEFAULT_USER})
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    return {
        "looking_at": portfolio.get("looking_at_industries", []),
        "avoiding": portfolio.get("avoiding_industries", []),
    }


@router.get("/interests", response_model=list[StockOfInterest])
async def get_stocks_of_interest(mongo=Depends(get_mongo)):
    """Get stocks the agent is watching with entry/exit points."""
    portfolio = await mongo.portfolios.find_one({"user_id": DEFAULT_USER})
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    return portfolio.get("stocks_of_interest", [])


@router.get("/performance")
async def get_performance(
    range: str = "1M",
    mongo=Depends(get_mongo),
):
    """
    Get portfolio performance data for charting.
    Range: 1D, 1W, 1M, 3M, 6M.

    NOTE: Full implementation requires historical portfolio snapshots.
    For now, returns the current state as a single data point.
    Full time-series will be added when the scheduler stores periodic snapshots.
    """
    portfolio = await mongo.portfolios.find_one({"user_id": DEFAULT_USER})
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Calculate current total value
    cash = portfolio.get("cash_balance", 0)
    holdings_value = sum(
        h.get("shares", 0) * h.get("avg_cost", 0)
        for h in portfolio.get("holdings", [])
    )
    total = cash + holdings_value

    return {
        "range": range,
        "current_value": total,
        "cash_balance": cash,
        "holdings_value": holdings_value,
        "data_points": [
            {
                "timestamp": portfolio.get("updated_at", "").isoformat()
                if portfolio.get("updated_at")
                else None,
                "value": total,
            }
        ],
        "note": "Full time-series requires periodic snapshots (coming in Phase 5)",
    }
