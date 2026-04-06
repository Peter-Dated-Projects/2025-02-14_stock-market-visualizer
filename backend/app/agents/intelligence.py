"""
Workflow 1 — Market Intelligence Gathering

Schedule: Every 60 minutes
Purpose: Scrape news, analyze sentiment per industry, update portfolio watchlists.

Flow:
  1. Fetch + deduplicate headlines from RSS feeds
  2. Group articles by industry
  3. Send batched text to Ollama for sentiment analysis
  4. Store results in agent_heuristics collection
  5. Update portfolio looking_at / avoiding industries
"""

import logging
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services import scraper
from app.services.ollama import generate_json

logger = logging.getLogger("smv.agent.intelligence")

SENTIMENT_PROMPT = """Analyze the following news headlines for the {industry} industry.
Rate the overall sentiment on a scale from -1.0 (very bearish) to +1.0 (very bullish).
Consider market impact, investor confidence, and recent trends.

Headlines:
{headlines}

Respond with JSON:
{{
  "industry": "{industry}",
  "sentiment": <float between -1.0 and 1.0>,
  "confidence": <int 0-100>,
  "reasoning": "<2-3 sentence summary>",
  "key_themes": ["<theme1>", "<theme2>"],
  "outlook": "bullish | bearish | neutral"
}}"""

SYSTEM_PROMPT = (
    "You are a financial market analyst. Analyze news headlines and provide "
    "objective sentiment assessments. Be data-driven and concise."
)


async def run(mongo: AsyncIOMotorDatabase) -> dict:
    """
    Execute the Market Intelligence workflow.
    Returns a summary of what was processed.
    """
    logger.info("Workflow 1: Market Intelligence — starting")
    start_time = datetime.utcnow()

    # 1. Fetch all news
    articles = await scraper.fetch_all_feeds()
    if not articles:
        logger.warning("No articles fetched — skipping analysis")
        return {"status": "no_data", "articles": 0}

    # 2. Group by industry
    grouped = scraper.group_by_industry(articles)
    logger.info(f"Grouped into {len(grouped)} industries")

    # 3. Analyze each industry with Ollama
    results = []
    for industry, industry_articles in grouped.items():
        if industry == "General Market":
            continue  # Skip unclassified

        # Build headline batch (limit to 15 per industry)
        headlines = "\n".join(
            f"- {a['title']} ({a['source']})"
            for a in industry_articles[:15]
        )

        prompt = SENTIMENT_PROMPT.format(industry=industry, headlines=headlines)
        analysis = await generate_json(prompt=prompt, system=SYSTEM_PROMPT)

        if analysis is None:
            logger.warning(f"Failed to analyze {industry}")
            continue

        # 4. Store in agent_heuristics
        heuristic = {
            "workflow": "intelligence",
            "ticker": None,
            "industry": industry,
            "input_summary": f"{len(industry_articles)} articles analyzed",
            "llm_prompt": prompt[:500],
            "llm_response": analysis,
            "sentiment_score": analysis.get("sentiment", 0),
            "action_recommended": analysis.get("outlook", "neutral").upper(),
            "confidence": analysis.get("confidence", 50),
            "created_at": datetime.utcnow(),
        }
        await mongo.agent_heuristics.insert_one(heuristic)
        results.append(heuristic)

        logger.info(
            f"  {industry}: sentiment={analysis.get('sentiment', 0):.2f}, "
            f"outlook={analysis.get('outlook', 'unknown')}"
        )

    # 5. Update portfolio industry lists
    await _update_portfolio_industries(mongo, results)

    elapsed = (datetime.utcnow() - start_time).total_seconds()
    summary = {
        "status": "completed",
        "articles_fetched": len(articles),
        "industries_analyzed": len(results),
        "elapsed_seconds": round(elapsed, 1),
    }
    logger.info(f"Workflow 1 complete: {summary}")
    return summary


async def _update_portfolio_industries(
    mongo: AsyncIOMotorDatabase, results: list[dict]
) -> None:
    """Update the portfolio's looking_at and avoiding industry lists."""
    looking_at = []
    avoiding = []

    for r in results:
        entry = {
            "name": r["industry"],
            "sentiment": r["sentiment_score"],
            "updated_at": datetime.utcnow(),
        }

        if r["sentiment_score"] >= 0.2:
            looking_at.append(entry)
        elif r["sentiment_score"] <= -0.2:
            reason = ""
            if r.get("llm_response"):
                reason = r["llm_response"].get("reasoning", "")
            entry["reason"] = reason
            avoiding.append(entry)

    # Sort by absolute sentiment (strongest signals first)
    looking_at.sort(key=lambda x: x["sentiment"], reverse=True)
    avoiding.sort(key=lambda x: x["sentiment"])

    if looking_at or avoiding:
        update = {"$set": {"updated_at": datetime.utcnow()}}
        if looking_at:
            update["$set"]["looking_at_industries"] = looking_at
        if avoiding:
            update["$set"]["avoiding_industries"] = avoiding

        await mongo.portfolios.update_one(
            {"user_id": "default_user"},
            update,
        )
        logger.info(
            f"Portfolio updated: watching {len(looking_at)} industries, "
            f"avoiding {len(avoiding)}"
        )
