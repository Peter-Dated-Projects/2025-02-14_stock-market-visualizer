#!/usr/bin/env bash
# ============================================================
# SMV — Local Development Launcher
# Usage: ./scripts/dev.sh [up|down|logs|restart|status]
# ============================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Default to staging env if no APP_ENV is set
export APP_ENV="${APP_ENV:-staging}"
ENV_FILE=".env.${APP_ENV}"

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ Environment file '$ENV_FILE' not found. Copy .env.example → $ENV_FILE and configure it."
  exit 1
fi

# Export env vars for docker compose
set -a
source "$ENV_FILE"
set +a

ACTION="${1:-up}"

case "$ACTION" in
  up)
    echo "🚀 Starting SMV in ${APP_ENV} mode..."
    docker compose --env-file "$ENV_FILE" up -d
    echo ""
    echo "✅ Services starting. Run './scripts/dev.sh logs' to tail output."
    echo ""
    echo "   MySQL:    localhost:3306"
    echo "   Redis:    localhost:6379"
    echo "   MongoDB:  localhost:27017"
    echo "   Ollama:   localhost:11434"
    echo "   Backend:  localhost:8000  (when backend container is added)"
    echo "   Frontend: localhost:3000  (when frontend container is added)"
    ;;
  down)
    echo "🛑 Stopping all SMV services..."
    docker compose --env-file "$ENV_FILE" down
    ;;
  logs)
    docker compose --env-file "$ENV_FILE" logs -f --tail=100
    ;;
  restart)
    echo "🔄 Restarting SMV services..."
    docker compose --env-file "$ENV_FILE" down
    docker compose --env-file "$ENV_FILE" up -d
    ;;
  status)
    docker compose --env-file "$ENV_FILE" ps
    ;;
  *)
    echo "Usage: $0 [up|down|logs|restart|status]"
    exit 1
    ;;
esac
