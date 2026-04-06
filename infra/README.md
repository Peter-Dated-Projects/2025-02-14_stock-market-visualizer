# Infrastructure — Database Setup & Migrations

## Overview

SMV uses three databases, each with a different migration strategy:

| Database | Purpose | Migration Tool |
|----------|---------|---------------|
| **MySQL 8.4** | Trade ledger (orders, fills, history) | Alembic (SQLAlchemy) |
| **MongoDB 7** | Users, portfolios, agent heuristics | Versioned scripts |
| **Redis 7** | Cache layer (no persistent schema) | N/A |

---

## MySQL — Alembic Migrations

### How It Works

1. **`infra/mysql/init.sql`** is the **v0 baseline** — it runs only on the very first container start (via Docker entrypoint). It creates the initial `trades` table and `trade_history_summary` view.

2. **All subsequent schema changes** go through Alembic, which lives in the backend:
   ```
   backend/
     alembic.ini
     alembic/
       env.py            # Reads DB config from app settings
       versions/         # Timestamped migration files
         001_add_xyz.py
         002_alter_abc.py
   ```

3. Alembic tracks what's been applied in a `alembic_version` table inside MySQL.

### Common Commands

```bash
# Generate a new migration after changing SQLAlchemy models
cd backend
uv run alembic revision --autogenerate -m "add_xyz_column"

# Apply all pending migrations
uv run alembic upgrade head

# Rollback the last migration
uv run alembic downgrade -1

# Show current migration status
uv run alembic current

# Show migration history
uv run alembic history
```

### Rules

- **Never manually ALTER the production database.** Always create an Alembic migration.
- **Never edit `init.sql` after first deploy.** It only runs once. Put changes in Alembic.
- **Test migrations locally first:** `docker compose down -v` to wipe volumes, then `docker compose up` to verify `init.sql` + all migrations run cleanly from scratch.
- Each migration file should have both `upgrade()` and `downgrade()` functions.

### Fresh Start (Nuke & Rebuild)

```bash
# Remove MySQL volume to reset to init.sql baseline
docker compose down -v
docker compose up -d mysql
# Then run Alembic migrations
cd backend && uv run alembic upgrade head
```

---

## MongoDB — Versioned Scripts

MongoDB is schemaless, so we don't need formal migrations for document structure changes. However, we **do** need migrations for:

- Index changes (add/remove/modify)
- Collection renames
- Data backfills or transformations
- Validator schema updates

### How It Works

1. **`infra/mongo/init-mongo.js`** is the baseline — it runs on first container start and creates collections, indexes, TTL policies, and seed data.

2. **Subsequent changes** use numbered scripts in `infra/mongo/migrations/`:
   ```
   infra/mongo/migrations/
     001_add_sentiment_index.js
     002_backfill_industry_field.js
   ```

3. Each script is idempotent (safe to re-run) and is applied manually or via a migration runner script.

### Running a Migration

```bash
# Connect to the running MongoDB container and execute
docker compose exec mongodb mongosh \
  -u ${MONGO_USER} -p ${MONGO_PASSWORD} \
  --authenticationDatabase admin \
  smv \
  /path/to/migration_script.js
```

### Rules

- Scripts must be **idempotent** — use `createIndex` (not `ensureIndex`), check for existence before inserting, etc.
- Prefix with a sequential number for ordering.
- Include a comment header with date, author, and description.

---

## Redis — No Migrations Needed

Redis is a pure cache layer with auto-expiring keys (TTL). There's no persistent schema to migrate. Configuration lives in `docker-compose.yml` (inline `redis-server` args).

Key TTL policies are enforced in application code (`backend/app/services/cache.py`):

| Key Pattern | TTL |
|------------|-----|
| `polygon:snapshot:{ticker}` | 5 min |
| `polygon:aggs:{ticker}:{date}` | 24 hours |
| `news:sentiment:{industry}` | 1 hour |
| `polygon:history:{ticker}` | 7 days |

---

## First-Time Setup Checklist

1. Copy `.env.example` → `.env.staging` and fill in credentials
2. Run `./scripts/dev.sh up` to start all services
3. Wait for healthchecks to pass: `./scripts/dev.sh status`
4. MySQL `init.sql` and Mongo `init-mongo.js` run automatically
5. Apply any Alembic migrations: `cd backend && uv run alembic upgrade head`
