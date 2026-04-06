"""
APScheduler job definitions.

Manages all recurring agent workflows with proper scheduling:
- Workflow 1 (Intelligence): Every 60 min
- Workflow 2 (Ingestion): Every 5 min, market hours only
- Workflow 3 (Signal): Every 15 min, market hours only
- Workflow 4 (Execution): Event-driven (triggered by 2 + 3)
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.dependencies import get_mongo, init_mysql, init_mongo, init_redis
from app.utils.market_hours import is_market_open

logger = logging.getLogger("smv.scheduler")

# Global scheduler instance
scheduler = AsyncIOScheduler()

# Track workflow runs for the system status API
workflow_status: dict[str, dict] = {
    "intelligence": {"last_run": None, "next_run": None, "status": "idle", "run_count": 0},
    "ingestion": {"last_run": None, "next_run": None, "status": "idle", "run_count": 0},
    "signal": {"last_run": None, "next_run": None, "status": "idle", "run_count": 0},
    "execution": {"last_run": None, "next_run": None, "status": "idle", "run_count": 0},
}


def _update_status(workflow: str, status: str) -> None:
    """Update the tracked status of a workflow."""
    workflow_status[workflow]["status"] = status
    if status == "running":
        workflow_status[workflow]["last_run"] = datetime.utcnow()
    workflow_status[workflow]["run_count"] += 1


# ──────────────────────────────────────────────
# Job wrappers
# ──────────────────────────────────────────────

async def job_intelligence():
    """Workflow 1: Market Intelligence Gathering (every 60 min)."""
    from app.agents import intelligence

    _update_status("intelligence", "running")
    try:
        mongo = get_mongo()
        result = await intelligence.run(mongo)
        _update_status("intelligence", "idle")
        logger.info(f"Intelligence job completed: {result.get('status')}")
    except Exception as e:
        _update_status("intelligence", "error")
        logger.error(f"Intelligence job failed: {e}")


async def job_ingestion():
    """Workflow 2: Ticker Data Ingestion (every 5 min, market hours)."""
    from app.agents import ingestion, execution
    from app.dependencies import get_mysql

    if not is_market_open():
        return

    _update_status("ingestion", "running")
    try:
        mongo = get_mongo()
        result = await ingestion.run(mongo)

        # If we got triggers, execute them
        triggers = result.get("trigger_details", [])
        if triggers:
            # We need a DB session for execution
            from app.dependencies import _session_factory
            if _session_factory:
                async with _session_factory() as db:
                    for trigger in triggers:
                        await execution.run(trigger=trigger, db=db, mongo=mongo)
                    await db.commit()

        _update_status("ingestion", "idle")
    except Exception as e:
        _update_status("ingestion", "error")
        logger.error(f"Ingestion job failed: {e}")


async def job_signal():
    """Workflow 3: Heuristic Signal Generation (every 15 min, market hours)."""
    from app.agents import signal, execution

    if not is_market_open():
        return

    _update_status("signal", "running")
    try:
        mongo = get_mongo()
        result = await signal.run(mongo)

        # If we got execution triggers, run them
        triggers = result.get("trigger_details", [])
        if triggers:
            from app.dependencies import _session_factory
            if _session_factory:
                async with _session_factory() as db:
                    for trigger in triggers:
                        await execution.run(trigger=trigger, db=db, mongo=mongo)
                    await db.commit()

        _update_status("signal", "idle")
    except Exception as e:
        _update_status("signal", "error")
        logger.error(f"Signal job failed: {e}")


# ──────────────────────────────────────────────
# Scheduler lifecycle
# ──────────────────────────────────────────────

def start_scheduler() -> None:
    """Configure and start the APScheduler."""
    if scheduler.running:
        return

    # Workflow 1: Every 60 minutes
    scheduler.add_job(
        job_intelligence,
        trigger=IntervalTrigger(minutes=60),
        id="intelligence",
        name="Market Intelligence",
        replace_existing=True,
    )

    # Workflow 2: Every 5 minutes
    scheduler.add_job(
        job_ingestion,
        trigger=IntervalTrigger(minutes=5),
        id="ingestion",
        name="Ticker Ingestion",
        replace_existing=True,
    )

    # Workflow 3: Every 15 minutes
    scheduler.add_job(
        job_signal,
        trigger=IntervalTrigger(minutes=15),
        id="signal",
        name="Signal Generation",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started with 3 recurring jobs")

    # Update next_run times
    for job in scheduler.get_jobs():
        if job.id in workflow_status:
            workflow_status[job.id]["next_run"] = job.next_run_time


def stop_scheduler() -> None:
    """Shut down the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
