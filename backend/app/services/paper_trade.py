"""
Paper Trading Engine.

Simulates order fills using live Polygon.io data.
In staging mode, all trades go through this engine instead of IBKR.

Fill assumptions:
- MARKET orders: fill at ask (BUY) or bid (SELL) — worst case for the trader
- LIMIT orders: fill at the target price (assumes limit is hit)
- STOP orders: fill at the target price
"""

import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.sql import Trade
from app.services import polygon

logger = logging.getLogger("smv.paper_trade")


class PaperTradeEngine:
    """Simulates order fills using live market data."""

    def __init__(self, db: AsyncSession, mongo: AsyncIOMotorDatabase) -> None:
        self.db = db
        self.mongo = mongo

    async def execute(
        self,
        user_id: str,
        ticker: str,
        action: str,
        quantity: float,
        order_type: str = "MARKET",
        target_price: float | None = None,
        confidence: int | None = None,
        reasoning: str | None = None,
        source_workflow: str | None = None,
    ) -> Trade:
        """
        Execute a paper trade.

        1. Fetch current market data from Polygon
        2. Determine fill price based on order type
        3. Validate against portfolio cash/holdings
        4. Update MongoDB portfolio (cash + holdings)
        5. Insert trade record into MySQL

        Returns the created Trade object.
        """
        # 1. Get current price data
        snapshot = await polygon.get_snapshot(ticker)
        if snapshot is None:
            raise ValueError(f"Cannot get market data for {ticker}")

        # 2. Determine fill price
        fill_price = self._calculate_fill_price(
            snapshot=snapshot,
            action=action,
            order_type=order_type,
            target_price=target_price,
        )

        # 3. Validate the trade
        portfolio = await self._get_portfolio(user_id)
        if portfolio is None:
            raise ValueError(f"Portfolio not found for user {user_id}")

        total_cost = fill_price * quantity

        if action == "BUY":
            if portfolio.get("cash_balance", 0) < total_cost:
                raise ValueError(
                    f"Insufficient cash: need ${total_cost:.2f}, "
                    f"have ${portfolio['cash_balance']:.2f}"
                )
        elif action == "SELL":
            held = self._get_held_shares(portfolio, ticker)
            if held < quantity:
                raise ValueError(
                    f"Insufficient shares: trying to sell {quantity}, "
                    f"hold {held} of {ticker}"
                )

        # 4. Update MongoDB portfolio
        await self._update_portfolio(
            user_id=user_id,
            ticker=ticker,
            action=action,
            quantity=quantity,
            fill_price=fill_price,
        )

        # 5. Insert trade record into MySQL
        trade = Trade(
            user_id=user_id,
            ticker=ticker.upper(),
            action=action,
            order_type=order_type,
            status="FILLED",  # Paper trades fill instantly
            quantity=Decimal(str(quantity)),
            target_price=Decimal(str(target_price)) if target_price else None,
            exec_price=Decimal(str(fill_price)),
            fees=Decimal("0"),  # No fees in paper trading
            paper_flag=True,
            source_workflow=source_workflow,
            confidence=confidence,
            reasoning=reasoning,
        )
        self.db.add(trade)
        await self.db.flush()
        await self.db.refresh(trade)

        logger.info(
            f"Paper trade executed: {action} {quantity} {ticker} "
            f"@ ${fill_price:.2f} (total: ${total_cost:.2f})"
        )

        return trade

    def _calculate_fill_price(
        self,
        snapshot: dict,
        action: str,
        order_type: str,
        target_price: float | None,
    ) -> float:
        """Determine fill price based on order type and action."""
        if order_type == "MARKET":
            # Worst-case fill for the trader
            if action == "BUY":
                price = snapshot.get("ask", 0) or snapshot.get("price", 0)
            else:
                price = snapshot.get("bid", 0) or snapshot.get("price", 0)
        elif order_type in ("LIMIT", "STOP"):
            if target_price is None:
                raise ValueError(f"{order_type} order requires a target_price")
            price = target_price
        else:
            raise ValueError(f"Unknown order type: {order_type}")

        if price <= 0:
            raise ValueError(f"Invalid fill price: {price}")

        return round(price, 4)

    async def _get_portfolio(self, user_id: str) -> dict | None:
        """Fetch user portfolio from MongoDB."""
        return await self.mongo.portfolios.find_one({"user_id": user_id})

    def _get_held_shares(self, portfolio: dict, ticker: str) -> float:
        """Get number of shares held for a ticker."""
        for holding in portfolio.get("holdings", []):
            if holding["ticker"].upper() == ticker.upper():
                return holding.get("shares", 0)
        return 0

    async def _update_portfolio(
        self,
        user_id: str,
        ticker: str,
        action: str,
        quantity: float,
        fill_price: float,
    ) -> None:
        """Update cash balance and holdings in MongoDB after a fill."""
        total_cost = fill_price * quantity
        ticker = ticker.upper()

        portfolio = await self._get_portfolio(user_id)
        if portfolio is None:
            return

        holdings = portfolio.get("holdings", [])
        existing = None
        for h in holdings:
            if h["ticker"].upper() == ticker:
                existing = h
                break

        if action == "BUY":
            new_cash = portfolio["cash_balance"] - total_cost

            if existing:
                # Update average cost
                old_total = existing["shares"] * existing["avg_cost"]
                new_total = old_total + total_cost
                new_shares = existing["shares"] + quantity
                existing["shares"] = new_shares
                existing["avg_cost"] = round(new_total / new_shares, 4)
            else:
                holdings.append({
                    "ticker": ticker,
                    "shares": quantity,
                    "avg_cost": round(fill_price, 4),
                })

        elif action == "SELL":
            new_cash = portfolio["cash_balance"] + total_cost

            if existing:
                existing["shares"] -= quantity
                if existing["shares"] <= 0:
                    holdings = [h for h in holdings if h["ticker"].upper() != ticker]

        await self.mongo.portfolios.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "cash_balance": round(new_cash, 2),
                    "holdings": holdings,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        logger.debug(
            f"Portfolio updated: {user_id} — cash=${new_cash:.2f}, "
            f"holdings={len(holdings)} positions"
        )
