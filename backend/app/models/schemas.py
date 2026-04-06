"""
Pydantic request/response schemas for the API.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Market Data Schemas
# ──────────────────────────────────────────────

class TickerSnapshot(BaseModel):
    ticker: str
    price: float
    bid: float
    ask: float
    volume: int
    change: float
    change_percent: float
    prev_close: float
    open: float
    high: float
    low: float
    timestamp: str


class AggregateBar(BaseModel):
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: int | None
    vwap: float | None
    transactions: int | None
    timestamp: str | None


class TickerDetails(BaseModel):
    ticker: str | None
    name: str | None
    description: str = ""
    industry: str = ""
    market_cap: float | None = None
    homepage: str | None = None
    locale: str | None = None
    type: str | None = None


# ──────────────────────────────────────────────
# Trade Schemas
# ──────────────────────────────────────────────

class TradeResponse(BaseModel):
    id: int
    user_id: str
    ticker: str
    action: str
    order_type: str
    status: str
    quantity: float
    target_price: float | None
    exec_price: float | None
    total_value: float | None
    fees: float
    paper_flag: bool
    source_workflow: str | None
    confidence: int | None
    reasoning: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TradeCreate(BaseModel):
    ticker: str = Field(..., max_length=10)
    action: str = Field(..., pattern="^(BUY|SELL)$")
    order_type: str = Field(default="MARKET", pattern="^(MARKET|LIMIT|STOP)$")
    quantity: float = Field(..., gt=0)
    target_price: float | None = None
    confidence: int | None = Field(default=None, ge=0, le=100)
    reasoning: str | None = None
    source_workflow: str | None = None


class TradeSummary(BaseModel):
    ticker: str
    total_trades: int
    first_trade: datetime | None
    last_trade: datetime | None
    total_bought: float
    total_sold: float


# ──────────────────────────────────────────────
# Portfolio Schemas
# ──────────────────────────────────────────────

class Holding(BaseModel):
    ticker: str
    shares: float
    avg_cost: float


class IndustrySentiment(BaseModel):
    name: str
    sentiment: float
    updated_at: datetime | None = None
    reason: str | None = None


class StockOfInterest(BaseModel):
    ticker: str
    industry: str
    entry_point: float | None = None
    exit_point: float | None = None
    confidence: int
    status: str  # WATCHING, ENTERED, EXITED


class PortfolioResponse(BaseModel):
    user_id: str
    cash_balance: float
    holdings: list[Holding]
    looking_at_industries: list[IndustrySentiment]
    avoiding_industries: list[IndustrySentiment]
    stocks_of_interest: list[StockOfInterest]
    updated_at: datetime | None = None


# ──────────────────────────────────────────────
# Agent Schemas
# ──────────────────────────────────────────────

class AgentLogEntry(BaseModel):
    id: str | None = None
    workflow: str
    ticker: str | None = None
    industry: str | None = None
    input_summary: str | None = None
    sentiment_score: float | None = None
    action_recommended: str | None = None
    confidence: int | None = None
    created_at: datetime | None = None


# ──────────────────────────────────────────────
# System Schemas
# ──────────────────────────────────────────────

class WorkflowStatus(BaseModel):
    name: str
    last_run: datetime | None = None
    next_run: datetime | None = None
    status: str = "idle"  # idle, running, error
    run_count: int = 0
