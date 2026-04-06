"""
Health check router — verifies all service connections.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_mysql, get_mongo, get_redis

router = APIRouter(tags=["system"])


@router.get("/health")
async def health_check():
    """Basic liveness probe — always returns OK if the server is running."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_mysql),
    mongo=Depends(get_mongo),
    redis=Depends(get_redis),
):
    """
    Deep readiness probe — checks all database connections.
    Returns per-service status so you can see exactly what's down.
    """
    checks = {}

    # MySQL
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        checks["mysql"] = "ok"
    except Exception as e:
        checks["mysql"] = f"error: {e}"

    # MongoDB
    try:
        await mongo.command("ping")
        checks["mongodb"] = "ok"
    except Exception as e:
        checks["mongodb"] = f"error: {e}"

    # Redis
    try:
        pong = await redis.ping()
        checks["redis"] = "ok" if pong else "error: no pong"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())

    return {
        "status": "ok" if all_ok else "degraded",
        "checks": checks,
    }
