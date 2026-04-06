"""
Workflow 3 — Heuristic Signal Generation

Schedule: Every 15 minutes (market hours only)
Purpose: Combine technical data + sentiment to generate BUY/SELL/HOLD signals.

Flow:
  1. For each ticker in stocks_of_interest, fetch price data from Redis
  2. Pull latest sentiment from agent_heuristics for the ticker's industry
  3. Call Ollama with combined technical + sentiment prompt
  4. If confidence >= 70: update entry/exit points in portfolio
  5. If confidence >= 85 + BUY/SELL: flag for Workflow 4 execution
"""

import logging
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services import polygon
from app.services.ollama import generate_json
from app.services.cache import cache_get, key_sentiment
from app.utils.market_hours import is_market_open

logger = logging.getLogger("smv.agent.signal")

SIGNAL_PROMPT = """You are a quantitative trading analyst. Analyze the following data for {ticker} and generate a trading signal.

## Current Market Data
- Price: ${price:.2f}
- Day Change: {change:+.2f}%
- Volume: {volume:,}
- Day Range: ${low:.2f} - ${high:.2f}
- Previous Close: ${prev_close:.2f}

## Industry Sentiment ({industry})
- Sentiment Score: {sentiment:.2f} (-1 bearish, +1 bullish)
- Industry Outlook: {outlook}

## Current Position
- Status: {status}
- Current Entry Point: {entry_point}
- Current Exit Point: {exit_point}

## Recent Heuristics
{recent_analysis}

Based on this data, provide a trading recommendation.

Respond with JSON:
{{
  "action": "BUY | SELL | HOLD",
  "confidence": <int 0-100>,
  "reasoning": "<3-4 sentence analysis>",
  "entry_point": <suggested entry price or null>,
  "exit_point": <suggested exit/target price or null>,
  "stop_loss": <suggested stop loss or null>,
  "risk_level": "low | medium | high",
  "timeframe": "short | medium | long"
}}"""

SYSTEM_PROMPT = (
    "You are a quantitative trading analyst. Make data-driven recommendations "
    "based on technical indicators and sentiment analysis. Be conservative — "
    "only recommend BUY or SELL with high confidence when there is strong supporting evidence. "
    "Default to HOLD when uncertain."
)


async def run(mongo: AsyncIOMotorDatabase) -> dict:
    """
    Execute the Signal Generation workflow.
    Returns summary with generated signals.
    """
    if not is_market_open():
        logger.debug("Workflow 3: Market closed — skipping")
        return {"status": "market_closed"}

    logger.info("Workflow 3: Signal Generation — starting")
    start_time = datetime.utcnow()

    portfolio = await mongo.portfolios.find_one({"user_id": "default_user"})
    if not portfolio:
        return {"status": "no_portfolio"}

    soi_list = portfolio.get("stocks_of_interest", [])
    if not soi_list:
        logger.info("No stocks of interest — skipping")
        return {"status": "no_tickers"}

    signals = []
    execution_triggers = []

    for soi in soi_list:
        ticker = soi["ticker"].upper()
        industry = soi.get("industry", "General")

        # 1. Get current price data
        snapshot = await polygon.get_snapshot(ticker)
        if not snapshot:
            logger.warning(f"No snapshot for {ticker} — skipping")
            continue

        # 2. Get latest industry sentiment
        sentiment_data = await _get_latest_sentiment(mongo, industry)

        # 3. Get recent heuristics for this ticker
        recent = await _get_recent_analysis(mongo, ticker)

        # 4. Generate signal via Ollama
        prompt = SIGNAL_PROMPT.format(
            ticker=ticker,
            price=snapshot.get("price", 0),
            change=snapshot.get("change_percent", 0),
            volume=snapshot.get("volume", 0),
            low=snapshot.get("low", 0),
            high=snapshot.get("high", 0),
            prev_close=snapshot.get("prev_close", 0),
            industry=industry,
            sentiment=sentiment_data.get("sentiment", 0),
            outlook=sentiment_data.get("outlook", "neutral"),
            status=soi.get("status", "WATCHING"),
            entry_point=soi.get("entry_point", "not set"),
            exit_point=soi.get("exit_point", "not set"),
            recent_analysis=recent,
        )

        signal = await generate_json(prompt=prompt, system=SYSTEM_PROMPT)
        if signal is None:
            logger.warning(f"Failed to generate signal for {ticker}")
            continue

        confidence = signal.get("confidence", 0)
        action = signal.get("action", "HOLD")

        # 5. Store in heuristics
        heuristic = {
            "workflow": "signal",
            "ticker": ticker,
            "industry": industry,
            "input_summary": f"Price ${snapshot.get('price', 0):.2f}, sentiment {sentiment_data.get('sentiment', 0):.2f}",
            "llm_prompt": prompt[:500],
            "llm_response": signal,
            "sentiment_score": sentiment_data.get("sentiment"),
            "action_recommended": action,
            "confidence": confidence,
            "created_at": datetime.utcnow(),
        }
        await mongo.agent_heuristics.insert_one(heuristic)
        signals.append(heuristic)

        logger.info(f"  {ticker}: {action} (confidence={confidence}%)")

        # 6. Update entry/exit if confidence >= 70
        if confidence >= 70:
            update_fields = {}
            if signal.get("entry_point"):
                update_fields["stocks_of_interest.$.entry_point"] = signal["entry_point"]
            if signal.get("exit_point"):
                update_fields["stocks_of_interest.$.exit_point"] = signal["exit_point"]
            if update_fields:
                await mongo.portfolios.update_one(
                    {"user_id": "default_user", "stocks_of_interest.ticker": ticker},
                    {"$set": update_fields},
                )

        # 7. High confidence + actionable → trigger execution
        if confidence >= 85 and action in ("BUY", "SELL"):
            execution_triggers.append({
                "ticker": ticker,
                "action": action,
                "confidence": confidence,
                "reasoning": signal.get("reasoning", ""),
                "source": "signal_workflow",
            })
            logger.info(f"  🚀 Triggering execution for {ticker}: {action} @ {confidence}% confidence")

    elapsed = (datetime.utcnow() - start_time).total_seconds()
    summary = {
        "status": "completed",
        "signals_generated": len(signals),
        "execution_triggers": len(execution_triggers),
        "trigger_details": execution_triggers,
        "elapsed_seconds": round(elapsed, 1),
    }
    logger.info(f"Workflow 3 complete: {len(signals)} signals, {len(execution_triggers)} triggers")
    return summary


async def _get_latest_sentiment(mongo: AsyncIOMotorDatabase, industry: str) -> dict:
    """Get the most recent sentiment analysis for an industry."""
    result = await mongo.agent_heuristics.find_one(
        {"workflow": "intelligence", "industry": industry},
        sort=[("created_at", -1)],
    )
    if result and result.get("llm_response"):
        return result["llm_response"]
    return {"sentiment": 0, "outlook": "neutral", "reasoning": "No data available"}


async def _get_recent_analysis(mongo: AsyncIOMotorDatabase, ticker: str) -> str:
    """Get recent analysis entries for context."""
    cursor = mongo.agent_heuristics.find(
        {"ticker": ticker},
        sort=[("created_at", -1)],
        limit=3,
    )
    entries = []
    async for doc in cursor:
        resp = doc.get("llm_response", {})
        if isinstance(resp, dict):
            entries.append(
                f"- [{doc.get('workflow', '?')}] {resp.get('action', '?')} "
                f"(confidence={resp.get('confidence', '?')}%): "
                f"{resp.get('reasoning', 'N/A')[:100]}"
            )
    return "\n".join(entries) if entries else "No recent analysis available"
