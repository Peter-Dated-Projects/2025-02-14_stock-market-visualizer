#!/usr/bin/env bash
# ============================================================
# SMV — Full Stack Runner
# Starts databases (Docker), backend (FastAPI), and frontend (Next.js)
#
# Usage:
#   ./run.sh              # Start everything
#   ./run.sh stop         # Stop everything
#   ./run.sh restart      # Restart everything
#   ./run.sh status       # Show status of all services
# ============================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

export APP_ENV="${APP_ENV:-staging}"
ENV_FILE=".env.${APP_ENV}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[SMV]${NC} $1"; }
ok()   { echo -e "${GREEN}  ✓${NC} $1"; }
warn() { echo -e "${YELLOW}  ⚠${NC} $1"; }
err()  { echo -e "${RED}  ✗${NC} $1"; }

# PID files for background processes
BACKEND_PID_FILE="$PROJECT_ROOT/.backend.pid"
FRONTEND_PID_FILE="$PROJECT_ROOT/.frontend.pid"

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

check_env() {
    if [ ! -f "$ENV_FILE" ]; then
        err "Environment file '$ENV_FILE' not found."
        echo "   Copy .env.example → $ENV_FILE and configure it."
        exit 1
    fi
    set -a; source "$ENV_FILE"; set +a
}

wait_for_service() {
    local name="$1" host="$2" port="$3" max_wait="${4:-30}"
    local elapsed=0
    while ! nc -z "$host" "$port" 2>/dev/null; do
        if [ $elapsed -ge $max_wait ]; then
            err "$name did not start within ${max_wait}s"
            return 1
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done
    ok "$name is ready (${elapsed}s)"
}

kill_pid_file() {
    local pid_file="$1" name="$2"
    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            # Also kill child processes
            pkill -P "$pid" 2>/dev/null || true
            ok "Stopped $name (PID $pid)"
        fi
        rm -f "$pid_file"
    fi
}

# ──────────────────────────────────────────────
# Start
# ──────────────────────────────────────────────

start_databases() {
    log "Starting databases (Docker)..."
    docker compose --env-file "$ENV_FILE" up -d
    echo ""

    log "Waiting for databases to be ready..."
    wait_for_service "MySQL"   localhost 3306 30
    wait_for_service "Redis"   localhost 6379 15
    wait_for_service "MongoDB" localhost 27017 15
    echo ""
}

start_backend() {
    log "Starting backend (FastAPI)..."

    # Kill existing if running
    kill_pid_file "$BACKEND_PID_FILE" "old backend"

    cd "$PROJECT_ROOT/backend"

    # Run uvicorn in the background
    uv run uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --log-level info \
        > "$PROJECT_ROOT/logs/backend.log" 2>&1 &

    echo $! > "$BACKEND_PID_FILE"
    cd "$PROJECT_ROOT"

    # Wait for backend to start
    wait_for_service "Backend" localhost 8000 15
}

start_frontend() {
    log "Starting frontend (Next.js)..."

    # Kill existing if running
    kill_pid_file "$FRONTEND_PID_FILE" "old frontend"

    if [ ! -d "$PROJECT_ROOT/frontend" ]; then
        warn "Frontend directory not found — skipping."
        warn "Frontend will be set up in Phase 6."
        return 0
    fi

    cd "$PROJECT_ROOT/frontend"

    # Copy env for Next.js
    cp "$PROJECT_ROOT/$ENV_FILE" .env.local 2>/dev/null || true

    bun run dev \
        > "$PROJECT_ROOT/logs/frontend.log" 2>&1 &

    echo $! > "$FRONTEND_PID_FILE"
    cd "$PROJECT_ROOT"

    wait_for_service "Frontend" localhost 3000 20
}

start_all() {
    check_env
    mkdir -p "$PROJECT_ROOT/logs"

    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     SMV — Stock Market Visualizer            ║${NC}"
    echo -e "${CYAN}║     Starting in ${YELLOW}${APP_ENV}${CYAN} mode                  ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
    echo ""

    start_databases
    start_backend
    start_frontend

    echo ""
    log "All services running:"
    echo ""
    echo -e "   ${GREEN}MySQL${NC}      http://localhost:3306"
    echo -e "   ${GREEN}Redis${NC}      http://localhost:6379"
    echo -e "   ${GREEN}MongoDB${NC}    http://localhost:27017"
    echo -e "   ${GREEN}Ollama${NC}     http://localhost:11434"
    echo -e "   ${GREEN}Backend${NC}    http://localhost:8000"
    echo -e "   ${GREEN}API Docs${NC}   http://localhost:8000/docs"
    if [ -d "$PROJECT_ROOT/frontend" ]; then
        echo -e "   ${GREEN}Frontend${NC}   http://localhost:3000"
    fi
    echo ""
    echo -e "   Logs:     ${CYAN}tail -f logs/backend.log${NC}"
    if [ -d "$PROJECT_ROOT/frontend" ]; then
        echo -e "             ${CYAN}tail -f logs/frontend.log${NC}"
    fi
    echo ""
}

# ──────────────────────────────────────────────
# Stop
# ──────────────────────────────────────────────

stop_all() {
    check_env
    echo ""
    log "Stopping all SMV services..."

    kill_pid_file "$FRONTEND_PID_FILE" "Frontend"
    kill_pid_file "$BACKEND_PID_FILE" "Backend"

    docker compose --env-file "$ENV_FILE" down
    ok "Databases stopped"

    echo ""
    log "All services stopped."
}

# ──────────────────────────────────────────────
# Status
# ──────────────────────────────────────────────

show_status() {
    check_env
    echo ""
    log "Service status:"
    echo ""

    # Docker services
    docker compose --env-file "$ENV_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || true
    echo ""

    # Backend
    if [ -f "$BACKEND_PID_FILE" ] && kill -0 "$(cat "$BACKEND_PID_FILE")" 2>/dev/null; then
        ok "Backend running (PID $(cat "$BACKEND_PID_FILE"))"
    else
        warn "Backend not running"
    fi

    # Frontend
    if [ -f "$FRONTEND_PID_FILE" ] && kill -0 "$(cat "$FRONTEND_PID_FILE")" 2>/dev/null; then
        ok "Frontend running (PID $(cat "$FRONTEND_PID_FILE"))"
    else
        warn "Frontend not running"
    fi
    echo ""
}

# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

ACTION="${1:-start}"

case "$ACTION" in
    start)   start_all ;;
    stop)    stop_all ;;
    restart) stop_all; start_all ;;
    status)  show_status ;;
    *)
        echo "Usage: $0 [start|stop|restart|status]"
        exit 1
        ;;
esac
