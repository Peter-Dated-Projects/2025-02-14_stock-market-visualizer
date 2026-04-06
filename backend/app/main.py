"""
FastAPI application factory with lifespan management.

The lifespan context manager initializes and tears down all database
connections, ensuring clean startup and shutdown.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.dependencies import (
    init_mysql, close_mysql,
    init_mongo, close_mongo,
    init_redis, close_redis,
)
from app.routers import health, market, trades, portfolio, agent, system
from app.services.polygon import close_client as close_polygon
from app.services.ollama import close_client as close_ollama
from app.agents.scheduler import start_scheduler, stop_scheduler

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG if settings.is_staging else logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("smv")


# ──────────────────────────────────────────────
# Lifespan — startup / shutdown
# ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all connections on startup, tear down on shutdown."""
    logger.info(f"Starting SMV backend [{settings.app_env}]")

    # Startup
    init_mysql()
    logger.info("  ✓ MySQL connected")

    init_mongo()
    logger.info("  ✓ MongoDB connected")

    init_redis()
    logger.info("  ✓ Redis connected")

    # Start agent scheduler
    start_scheduler()
    logger.info("  ✓ Agent scheduler started")

    logger.info("All services initialized. Ready to serve requests.")

    yield

    # Shutdown
    logger.info("Shutting down SMV backend...")
    stop_scheduler()
    await close_mysql()
    await close_mongo()
    await close_redis()
    await close_polygon()
    await close_ollama()
    logger.info("All connections closed. Goodbye.")


# ──────────────────────────────────────────────
# App factory
# ──────────────────────────────────────────────

def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="SMV — Stock Market Visualizer",
        description="Automated trading platform with AI-driven market intelligence",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.is_staging else None,
        redoc_url="/redoc" if settings.is_staging else None,
    )

    # CORS — allow frontend in development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(health.router)
    app.include_router(market.router)
    app.include_router(trades.router)
    app.include_router(portfolio.router)
    app.include_router(agent.router)
    app.include_router(system.router)

    return app


# Uvicorn entrypoint
app = create_app()
