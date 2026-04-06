"""
System routes — workflow status, schedule, and trigger management.
"""

from fastapi import APIRouter

from app.agents.scheduler import scheduler, workflow_status
from app.utils.market_hours import is_market_open, is_trading_day, minutes_until_open, minutes_until_close

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/workflows")
async def get_workflows():
    """Get workflow definitions and current run status."""
    workflows = []
    for name, status in workflow_status.items():
        workflows.append({
            "name": name,
            "last_run": status["last_run"],
            "next_run": status["next_run"],
            "status": status["status"],
            "run_count": status["run_count"],
        })
    return {"workflows": workflows}


@router.get("/schedule")
async def get_schedule():
    """Get upcoming trigger times for all scheduled jobs."""
    jobs = []
    if scheduler.running:
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time,
                "trigger": str(job.trigger),
            })

    return {
        "scheduler_running": scheduler.running,
        "jobs": jobs,
        "market": {
            "is_open": is_market_open(),
            "is_trading_day": is_trading_day(),
            "minutes_until_open": minutes_until_open(),
            "minutes_until_close": minutes_until_close(),
        },
    }
