"""
Agent routes — agent heuristic logs and latest thoughts.
"""

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_mongo

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.get("/logs")
async def get_agent_logs(
    workflow: str | None = Query(default=None, pattern="^(intelligence|ingestion|signal|execution)$"),
    ticker: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    mongo=Depends(get_mongo),
):
    """Get agent heuristic log entries, newest first."""
    query = {}
    if workflow:
        query["workflow"] = workflow
    if ticker:
        query["ticker"] = ticker.upper()

    cursor = mongo.agent_heuristics.find(
        query,
        sort=[("created_at", -1)],
        limit=limit,
    )

    logs = []
    async for doc in cursor:
        logs.append({
            "id": str(doc["_id"]),
            "workflow": doc.get("workflow"),
            "ticker": doc.get("ticker"),
            "industry": doc.get("industry"),
            "input_summary": doc.get("input_summary"),
            "sentiment_score": doc.get("sentiment_score"),
            "action_recommended": doc.get("action_recommended"),
            "confidence": doc.get("confidence"),
            "llm_response": doc.get("llm_response"),
            "created_at": doc.get("created_at"),
        })

    return {"logs": logs, "count": len(logs)}


@router.get("/latest-thoughts")
async def get_latest_thoughts(
    mongo=Depends(get_mongo),
):
    """
    Get the most recent LLM reasoning per active ticker.
    Used for the dashboard 'agent thinking' display.
    """
    # Get distinct tickers with recent activity
    pipeline = [
        {"$match": {"ticker": {"$ne": None}}},
        {"$sort": {"created_at": -1}},
        {"$group": {
            "_id": "$ticker",
            "latest": {"$first": "$$ROOT"},
        }},
        {"$limit": 20},
    ]

    thoughts = []
    async for doc in mongo.agent_heuristics.aggregate(pipeline):
        latest = doc["latest"]
        llm_resp = latest.get("llm_response", {})
        reasoning = ""
        if isinstance(llm_resp, dict):
            reasoning = llm_resp.get("reasoning", "")

        thoughts.append({
            "ticker": doc["_id"],
            "workflow": latest.get("workflow"),
            "action": latest.get("action_recommended"),
            "confidence": latest.get("confidence"),
            "reasoning": reasoning,
            "created_at": latest.get("created_at"),
        })

    return {"thoughts": thoughts}
