#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# Sonic Player — Start Script
# Starts both Frontend (Next.js :3004) + Backend (FastAPI :8005)
# ═══════════════════════════════════════════════════════════

set +e  # Don't exit on error - we handle them

# ── Kill any existing processes on our ports ──
fuser -k 8005/tcp 2>/dev/null >/dev/null
fuser -k 3004/tcp 2>/dev/null >/dev/null
sleep 1

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "  ${CYAN}┌──────────────────────────┐${NC}"
echo -e "  ${CYAN}│${NC}  ${BOLD}🎵 Sonic Player${NC}          ${CYAN}│${NC}"
echo -e "  ${CYAN}│${NC}  by CYBER-HACKER-Studio   ${CYAN}│${NC}"
echo -e "  ${CYAN}└──────────────────────────┘${NC}"
echo -e "  ${YELLOW}⚠ For personal/educational use only.${NC}"
echo -e "  ${YELLOW}  Users must comply with YouTube ToS.${NC}"
echo ""

# ── Check if install needed ──
if [ ! -d "node_modules" ] || [ ! -f "backend/requirements.txt" ]; then
  echo -e "  ${YELLOW}⚠ Dependencies not found. Running install first...${NC}"
  bash install.sh
  echo ""
fi

# ── Detect Python command ──
if command -v python3 &>/dev/null; then
  PYTHON=python3
else
  PYTHON=python
fi

# ── Start Backend ──
echo -e "  ${GREEN}━━━${NC} ${BOLD}Starting Backend (port 8005)...${NC}"
cd backend
$PYTHON main.py &
BACKEND_PID=$!
cd ..
sleep 2
if kill -0 "$BACKEND_PID" 2>/dev/null; then
  echo -e "  ${GREEN}✓${NC} Backend running on http://localhost:8005"
else
  echo -e "  ${RED}✗${NC} Backend failed to start"
  exit 1
fi

# ── Start Frontend ──
echo -e "  ${GREEN}━━━${NC} ${BOLD}Starting Frontend (port 3004)...${NC}"
npx next start -p 3004 &
FRONTEND_PID=$!
sleep 3
if kill -0 "$FRONTEND_PID" 2>/dev/null; then
  echo -e "  ${GREEN}✓${NC} Frontend running on http://localhost:3004"
else
  echo -e "  ${YELLOW}⚠${NC} Frontend starting... trying dev mode"
  npx next dev -p 3004 &
  FRONTEND_PID=$!
  sleep 4
fi

echo ""
echo -e "  ${CYAN}┌─────────────────────────────────────┐${NC}"
echo -e "  ${CYAN}│${NC}  🌐  ${BOLD}http://localhost:3004${NC}              ${CYAN}│${NC}"
echo -e "  ${CYAN}│${NC}  ⚙️   ${BOLD}http://localhost:8005${NC}              ${CYAN}│${NC}"
echo -e "  ${CYAN}└─────────────────────────────────────┘${NC}"
echo ""
echo -e "  ${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Trap to kill both on exit
cleanup() {
  echo ""
  echo -e "  ${CYAN}→${NC} Stopping services..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
  echo -e "  ${GREEN}✓${NC} Stopped."
  exit 0
}
trap cleanup SIGINT SIGTERM

wait
