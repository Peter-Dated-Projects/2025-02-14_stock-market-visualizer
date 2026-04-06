# SMV — Stock Market Visualizer

An automated trading platform with AI-driven market intelligence, paper trading, and a real-time dashboard.

```
┌──────────────────────────────────────────────────────────────────┐
│                        SMV Architecture                         │
│                                                                  │
│  ┌─────────┐  RSS    ┌──────────┐  LLM    ┌──────────┐         │
│  │  Yahoo   │───────▶│  Agent   │────────▶│  Ollama  │         │
│  │  Reddit  │        │  Engine  │         │  (local) │         │
│  │  SEC     │        │          │         └──────────┘         │
│  └─────────┘        │  4 workflows:                            │
│                      │  1. Intelligence                         │
│  ┌──────────┐        │  2. Ingestion    ┌──────────┐           │
│  │ Polygon  │───────▶│  3. Signal  ────▶│  Paper   │           │
│  │   API    │  REST  │  4. Execution    │  Trade   │           │
│  └──────────┘        └───────┬──────────┘  Engine  │           │
│                              │             └────┬───┘           │
│                              │                  │               │
│       ┌──────────┬───────────┼──────────────────┘               │
│       ▼          ▼           ▼                                  │
│  ┌────────┐ ┌────────┐ ┌────────┐                              │
│  │ MySQL  │ │ Mongo  │ │ Redis  │                              │
│  │ trades │ │ portf. │ │ cache  │                              │
│  └────────┘ └────────┘ └────────┘                              │
│       │          │           │                                  │
│       └──────────┼───────────┘                                  │
│                  ▼                                              │
│          ┌──────────────┐     ┌──────────────┐                 │
│          │   FastAPI    │────▶│   Next.js    │                 │
│          │   Backend    │ API │   Frontend   │                 │
│          │  18 routes   │     │  5 pages     │                 │
│          └──────────────┘     └──────────────┘                 │
└──────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env.staging
# Edit .env.staging with your API keys

# 2. Start everything
./run.sh

# 3. Open the dashboard
open http://localhost:3000
```

## Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 16, TypeScript, Recharts |
| **Backend** | FastAPI, Python 3.12, UV |
| **Databases** | MySQL 8.4, MongoDB 7, Redis 7 |
| **AI** | Ollama (local LLM) |
| **Trading** | Polygon.io (market data), IBKR (live — future) |
| **Migrations** | Alembic (MySQL), versioned scripts (MongoDB) |
| **Infra** | Docker Compose |

## Project Structure

```
smv/
├── run.sh                    # Full-stack start/stop script
├── docker-compose.yml        # MySQL, Redis, MongoDB, Ollama
├── .env.staging              # Staging environment config
├── .env.production           # Production environment config
│
├── backend/
│   ├── pyproject.toml        # UV project — Python dependencies
│   ├── Dockerfile
│   ├── alembic.ini           # Migration config
│   ├── alembic/
│   │   └── env.py            # Alembic environment
│   └── app/
│       ├── main.py           # App factory + lifespan
│       ├── config.py         # Pydantic settings
│       ├── dependencies.py   # DB connection injection
│       ├── models/
│       │   ├── sql.py        # SQLAlchemy ORM (trades)
│       │   └── schemas.py    # Pydantic request/response schemas
│       ├── routers/
│       │   ├── health.py     # GET /health, /health/ready
│       │   ├── market.py     # GET /api/market/*
│       │   ├── trades.py     # GET/POST /api/trades/*
│       │   ├── portfolio.py  # GET /api/portfolio/*
│       │   ├── agent.py      # GET /api/agent/*
│       │   └── system.py     # GET /api/system/*
│       ├── services/
│       │   ├── polygon.py    # Polygon.io API client
│       │   ├── cache.py      # Redis caching layer
│       │   ├── ollama.py     # Ollama LLM client
│       │   ├── scraper.py    # RSS/news scraper
│       │   └── paper_trade.py # Paper trading engine
│       ├── agents/
│       │   ├── intelligence.py  # Workflow 1: Market Intelligence
│       │   ├── ingestion.py     # Workflow 2: Ticker Ingestion
│       │   ├── signal.py        # Workflow 3: Signal Generation
│       │   ├── execution.py     # Workflow 4: Trade Execution
│       │   └── scheduler.py     # APScheduler job definitions
│       └── utils/
│           └── market_hours.py  # NYSE trading hours
│
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── layout.tsx          # Root layout
│       │   ├── globals.css         # Design system (700+ lines)
│       │   ├── page.tsx            # Dashboard
│       │   ├── portfolio/page.tsx
│       │   ├── trades/page.tsx
│       │   ├── agent-logic/page.tsx
│       │   └── system-graph/page.tsx
│       ├── components/
│       │   ├── layout/
│       │   │   ├── AppShell.tsx
│       │   │   ├── Sidebar.tsx
│       │   │   ├── Topbar.tsx
│       │   │   └── ThemeToggle.tsx
│       │   └── dashboard/
│       │       ├── PortfolioHeader.tsx
│       │       ├── PerformanceChart.tsx
│       │       ├── IndustryRadar.tsx
│       │       ├── StocksOfInterest.tsx
│       │       ├── ActivePositions.tsx
│       │       └── RecentTrades.tsx
│       ├── hooks/
│       │   ├── useTheme.ts
│       │   ├── useApi.ts
│       │   └── useWebSocket.ts
│       └── lib/
│           ├── api.ts
│           └── formatters.ts
│
├── infra/
│   ├── README.md             # Migration strategy docs
│   ├── mysql/init.sql        # Initial schema (v0 baseline)
│   └── mongo/init-mongo.js   # Collections + indexes + seed
│
└── scripts/
    └── dev.sh                # Docker management helper
```

## API Reference

### Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/health/ready` | Deep readiness (pings all DBs) |

### Market Data
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/market/snapshot/{ticker}` | Current price, bid/ask, volume |
| GET | `/api/market/aggregates/{ticker}` | OHLCV bars for charting |
| GET | `/api/market/details/{ticker}` | Company info, market cap |
| GET | `/api/market/batch-snapshot` | Multiple tickers at once |

### Trades
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/trades/` | Paginated trade history |
| POST | `/api/trades/` | Execute a trade |
| GET | `/api/trades/recent` | Last N trades |
| GET | `/api/trades/summary/{ticker}` | Aggregate stats per ticker |

### Portfolio
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/portfolio/` | Full portfolio state |
| GET | `/api/portfolio/industries` | Industry sentiments |
| GET | `/api/portfolio/interests` | Stocks of interest |
| GET | `/api/portfolio/performance` | Performance data |

### Agent
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/agent/logs` | Agent heuristic log |
| GET | `/api/agent/latest-thoughts` | Latest reasoning per ticker |

### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/system/workflows` | Workflow run status |
| GET | `/api/system/schedule` | Upcoming job schedule |

## Agent Workflows

The platform runs 4 autonomous workflows:

| # | Workflow | Schedule | What it does |
|---|----------|----------|--------------|
| 1 | **Intelligence** | Every 60 min | Scrapes RSS feeds → groups by industry → Ollama sentiment analysis → updates watchlists |
| 2 | **Ingestion** | Every 5 min (market hours) | Fetches live prices → caches in Redis → detects entry/exit crossings |
| 3 | **Signal** | Every 15 min (market hours) | Combines price + sentiment → generates BUY/SELL/HOLD via Ollama → updates entry/exit points |
| 4 | **Execution** | Event-driven | Receives triggers from #2 and #3 → position sizing → paper trade execution |

## Development

```bash
# Backend only
cd backend && uv run uvicorn app.main:app --reload

# Frontend only
cd frontend && bun run dev

# Databases only
docker compose --env-file .env.staging up -d

# Run migrations
cd backend && uv run alembic upgrade head

# All at once
./run.sh
```

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Description |
|----------|-------------|
| `APP_ENV` | `staging` or `production` |
| `POLYGON_API_KEY` | Polygon.io API key (free tier works) |
| `PAPER_TRADE_ENABLED` | `true` for paper, `false` for live IBKR |
| `MYSQL_*` | MySQL connection settings |
| `MONGO_*` | MongoDB connection settings |
| `OLLAMA_MODEL` | LLM model name (default: `llama3.2`) |

## License

MIT
