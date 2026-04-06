"""
Workflow 4 — Trade Execution Pipeline

Trigger: Event-driven (from Workflow 2 price crossings or Workflow 3 high-confidence signals)
Purpose: Execute trades via paper trading engine (staging) or IBKR (production).

Flow:
  1. Receive trigger event (ticker, action, confidence, reasoning)
  2. Determine trade quantity based on position sizing rules
  3. Execute via PaperTradeEngine or IBKR
  4. Log result to agent_heuristics
"""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.services.paper_trade import PaperTradeEngine
from app.services import polygon

logger = logging.getLogger("smv.agent.execution")

# Position sizing rules
MAX_POSITION_PCT = 0.10     # Max 10% of portfolio in a single position
MAX_TRADE_VALUE = 10000.00  # Max $10k per trade
MIN_TRADE_VALUE = 100.00    # Min $100 per trade
DEFAULT_QUANTITY = 1        # Fallback quantity


async def run(
    trigger: dict,
    db: AsyncSession,
    mongo: AsyncIOMotorDatabase,
) -> dict:
    """
    Execute a trade based on a trigger event.

    trigger = {
        "ticker": "NVDA",
        "action": "BUY",
        "confidence": 87,
        "reasoning": "Strong AI sector momentum...",
        "source": "signal_workflow" | "ingestion_crossing",
    }
    """
    ticker = trigger["ticker"].upper()
    action = trigger["action"]
    confidence = trigger.get("confidence", 0)
    reasoning = trigger.get("reasoning", "")
    source = trigger.get("source", "unknown")

    logger.info(f"Workflow 4: Executing {action} {ticker} (confidence={confidence}%, source={source})")

    try:
        # 1. Get current portfolio state
        portfolio = await mongo.portfolios.find_one({"user_id": "default_user"})
        if not portfolio:
            raise ValueError("Portfolio not found")

        # 2. Get current price
        snapshot = await polygon.get_snapshot(ticker)
        if not snapshot:
            raise ValueError(f"Cannot get price for {ticker}")

        price = snapshot.get("price", 0)
        if price <= 0:
            raise ValueError(f"Invalid price for {ticker}: {price}")

        # 3. Calculate quantity
        quantity = _calculate_quantity(
            portfolio=portfolio,
            ticker=ticker,
            action=action,
            price=price,
        )

        if quantity <= 0:
            logger.warning(f"Calculated 0 quantity for {ticker} — skipping")
            return {"status": "skipped", "reason": "zero_quantity"}

        # 4. Execute the trade
        if settings.paper_trade_enabled:
            engine = PaperTradeEngine(db=db, mongo=mongo)
            trade = await engine.execute(
                user_id="default_user",
                ticker=ticker,
                action=action,
                quantity=quantity,
                order_type="MARKET",
                confidence=confidence,
                reasoning=reasoning,
                source_workflow=source,
            )

            result = {
                "status": "executed",
                "trade_id": trade.id,
                "ticker": ticker,
                "action": action,
                "quantity": float(trade.quantity),
                "price": float(trade.exec_price),
                "total": float(trade.quantity * trade.exec_price),
                "paper": True,
            }
        else:
            # IBKR execution — stub for now
            logger.warning("IBKR execution not yet implemented")
            return {"status": "skipped", "reason": "ibkr_not_implemented"}

        # 5. Log to agent_heuristics
        await mongo.agent_heuristics.insert_one({
            "workflow": "execution",
            "ticker": ticker,
            "industry": None,
            "input_summary": f"{action} {quantity} shares @ ${price:.2f}",
            "llm_prompt": None,
            "llm_response": result,
            "sentiment_score": None,
            "action_recommended": action,
            "confidence": confidence,
            "created_at": datetime.utcnow(),
        })

        # 6. Update stock of interest status
        if action == "BUY":
            await mongo.portfolios.update_one(
                {"user_id": "default_user", "stocks_of_interest.ticker": ticker},
                {"$set": {"stocks_of_interest.$.status": "ENTERED"}},
            )
        elif action == "SELL":
            await mongo.portfolios.update_one(
                {"user_id": "default_user", "stocks_of_interest.ticker": ticker},
                {"$set": {"stocks_of_interest.$.status": "EXITED"}},
            )

        logger.info(
            f"Trade executed: {action} {quantity} {ticker} @ ${price:.2f} "
            f"(total: ${quantity * price:.2f})"
        )
        return result

    except Exception as e:
        logger.error(f"Execution failed for {ticker}: {e}")

        # Log the failure
        await mongo.agent_heuristics.insert_one({
            "workflow": "execution",
            "ticker": ticker,
            "industry": None,
            "input_summary": f"FAILED: {action} {ticker} — {str(e)}",
            "llm_prompt": None,
            "llm_response": {"error": str(e)},
            "sentiment_score": None,
            "action_recommended": action,
            "confidence": confidence,
            "created_at": datetime.utcnow(),
        })

        return {"status": "error", "error": str(e)}


def _calculate_quantity(
    portfolio: dict,
    ticker: str,
    action: str,
    price: float,
) -> float:
    """
    Calculate trade quantity based on position sizing rules.

    For BUY: size based on available cash and max position percentage.
    For SELL: sell all held shares.
    """
    if action == "SELL":
        # Sell all shares held
        for h in portfolio.get("holdings", []):
            if h["ticker"].upper() == ticker:
                return h.get("shares", 0)
        return 0

    # BUY — position sizing
    cash = portfolio.get("cash_balance", 0)
    total_value = cash + sum(
        h.get("shares", 0) * h.get("avg_cost", 0)
        for h in portfolio.get("holdings", [])
    )

    # Max position = 10% of portfolio value
    max_position_value = total_value * MAX_POSITION_PCT

    # Check existing position
    existing_value = 0
    for h in portfolio.get("holdings", []):
        if h["ticker"].upper() == ticker:
            existing_value = h.get("shares", 0) * price
            break

    # Remaining room in this position
    remaining_room = max_position_value - existing_value

    # Cap to max trade value and available cash
    trade_value = min(remaining_room, MAX_TRADE_VALUE, cash * 0.9)  # Keep 10% cash buffer

    if trade_value < MIN_TRADE_VALUE:
        return 0

    quantity = int(trade_value / price)  # Whole shares only
    return max(quantity, 0)
