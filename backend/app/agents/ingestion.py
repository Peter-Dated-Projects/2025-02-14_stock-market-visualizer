"""
Workflow 2 — Ticker Data Ingestion

Schedule: Every 5 minutes (market hours only)
Purpose: Fetch current prices for all active tickers, cache in Redis,
         and check for entry/exit point crossings.

Flow:
  1. Read active tickers from portfolio holdings + stocks_of_interest
  2. Batch fetch snapshots from Polygon.io
  3. Write to Redis cache (handled by polygon client)
  4. Check if any price crosses entry/exit points → flag for Workflow 4
"""

import logging
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services import polygon
from app.utils.market_hours import is_market_open

logger = logging.getLogger("smv.agent.ingestion")


async def run(mongo: AsyncIOMotorDatabase) -> dict:
    """
    Execute the Ticker Data Ingestion workflow.
    Returns summary with any triggered signals.
    """
    if not is_market_open():
        logger.debug("Workflow 2: Market closed — skipping")
        return {"status": "market_closed"}

    logger.info("Workflow 2: Ticker Ingestion — starting")
    start_time = datetime.utcnow()

    # 1. Get active tickers
    portfolio = await mongo.portfolios.find_one({"user_id": "default_user"})
    if not portfolio:
        return {"status": "no_portfolio"}

    tickers = set()

    # From holdings
    for h in portfolio.get("holdings", []):
        tickers.add(h["ticker"].upper())

    # From stocks of interest
    for s in portfolio.get("stocks_of_interest", []):
        tickers.add(s["ticker"].upper())

    if not tickers:
        logger.info("No active tickers to ingest")
        return {"status": "no_tickers"}

    logger.info(f"Ingesting data for {len(tickers)} tickers: {tickers}")

    # 2. Batch fetch snapshots (this also caches in Redis)
    snapshots = await polygon.get_batch_snapshots(list(tickers))

    # 3. Check for entry/exit point crossings
    triggers = []
    for soi in portfolio.get("stocks_of_interest", []):
        ticker = soi["ticker"].upper()
        snap = snapshots.get(ticker)
        if not snap:
            continue

        current_price = snap.get("price", 0)
        entry_point = soi.get("entry_point")
        exit_point = soi.get("exit_point")

        # Entry point crossing (price drops to or below entry)
        if entry_point and current_price <= entry_point and soi.get("status") == "WATCHING":
            triggers.append({
                "ticker": ticker,
                "type": "entry_crossed",
                "price": current_price,
                "target": entry_point,
                "action": "BUY",
            })
            logger.info(f"  🔔 {ticker} crossed entry point: ${current_price:.2f} <= ${entry_point:.2f}")

        # Exit point crossing (price rises to or above exit) for held positions
        if exit_point and current_price >= exit_point:
            # Check if we actually hold this
            held = any(h["ticker"].upper() == ticker for h in portfolio.get("holdings", []))
            if held:
                triggers.append({
                    "ticker": ticker,
                    "type": "exit_crossed",
                    "price": current_price,
                    "target": exit_point,
                    "action": "SELL",
                })
                logger.info(f"  🔔 {ticker} crossed exit point: ${current_price:.2f} >= ${exit_point:.2f}")

    # Store trigger events in heuristics log
    for trigger in triggers:
        await mongo.agent_heuristics.insert_one({
            "workflow": "ingestion",
            "ticker": trigger["ticker"],
            "industry": None,
            "input_summary": f"Price ${trigger['price']:.2f} crossed {trigger['type']} @ ${trigger['target']:.2f}",
            "llm_prompt": None,
            "llm_response": trigger,
            "sentiment_score": None,
            "action_recommended": trigger["action"],
            "confidence": 90,  # Price crossings are high confidence
            "created_at": datetime.utcnow(),
        })

    elapsed = (datetime.utcnow() - start_time).total_seconds()
    summary = {
        "status": "completed",
        "tickers_ingested": len(snapshots),
        "triggers": len(triggers),
        "trigger_details": triggers,
        "elapsed_seconds": round(elapsed, 1),
    }
    logger.info(f"Workflow 2 complete: {len(snapshots)} tickers, {len(triggers)} triggers")
    return summary
