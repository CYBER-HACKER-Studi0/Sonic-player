#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# Sonic Player — Setup & Install Script
# Works on Linux, macOS, and Termux (Android)
# ═══════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# Detect OS
detect_os() {
  if [ -n "$TERMUX_VERSION" ]; then
    echo "termux"
  elif [ "$(uname)" = "Darwin" ]; then
    echo "macos"
  elif [ "$(uname)" = "Linux" ]; then
    echo "linux"
  else
    echo "unknown"
  fi
}

OS=$(detect_os)

print_banner() {
  echo ""
  echo -e "  ${CYAN}┌──────────────────────────┐${NC}"
  echo -e "  ${CYAN}│${NC}  ${BOLD}🎵 Sonic Player${NC}          ${CYAN}│${NC}"
  echo -e "  ${CYAN}│${NC}  by CYBER-HACKER-Studio   ${CYAN}│${NC}"
  echo -e "  ${CYAN}└──────────────────────────┘${NC}"
  echo ""
  echo -e "  ${PURPLE}📱${NC} OS Detected: ${BOLD}$OS${NC}"
  echo ""
}

step() {
  echo -e "\n  ${GREEN}━━━${NC} ${BOLD}$1${NC}"
}

info() {
  echo -e "  ${CYAN}→${NC} $1"
}

ok() {
  echo -e "  ${GREEN}✓${NC} $1"
}

warn() {
  echo -e "  ${YELLOW}⚠${NC} $1"
}

fail() {
  echo -e "  ${RED}✗${NC} $1"
}

spinner() {
  local pid=$1
  local msg=$2
  local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
  local i=0
  while kill -0 "$pid" 2>/dev/null; do
    printf "\r  ${CYAN}%s${NC} %s" "${spin:$i:1}" "$msg"
    i=$(( (i+1) % ${#spin} ))
    sleep 0.1
  done
  printf "\r${GREEN}  ✓${NC} %-50s\n" "$msg"
}

# ─────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────

print_banner

# ── 1. System Dependencies ──
step "1/5  Checking System Dependencies"

if [ "$OS" = "termux" ]; then
  PKG_MANAGER="pkg"
  PKG_INSTALL="$PKG_MANAGER install -y"
  
  # Check if pkg is available
  if ! command -v pkg &>/dev/null; then
    fail "pkg not found. Are you in Termux?"
    exit 1
  fi

  for dep in nodejs python ffmpeg; do
    if command -v "$dep" &>/dev/null; then
      ok "$dep already installed"
    else
      info "Installing $dep..."
      $PKG_INSTALL "$dep" 2>&1 | tail -1 >/dev/null
      ok "$dep installed"
    fi
  done
else
  # Linux / macOS
  for dep in node python3; do
    if command -v "$dep" &>/dev/null; then
      ok "$dep $(command -v $dep)"
    else
      fail "$dep not found. Please install Node.js 18+ and Python 3."
      exit 1
    fi
  done

  # Check ffmpeg
  if command -v ffmpeg &>/dev/null; then
    ok "ffmpeg $(ffmpeg -version 2>&1 | head -1 | grep -oP 'version \K[^ ]+' || echo 'found')"
  else
    warn "ffmpeg not found. Install: sudo apt install ffmpeg (Linux) or brew install ffmpeg (macOS)"
  fi
fi

# ── 2. Python Backend Dependencies ──
step "2/5  Installing Python Backend Packages"

cd "$(dirname "$0")"

if [ "$OS" = "termux" ]; then
  PYTHON=python
  PIP="python -m pip"
  # Install pip if missing
  if ! $PYTHON -m pip --version &>/dev/null; then
    info "Installing python-pip..."
    pkg install -y python-pip 2>&1 | tail -1 >/dev/null
  fi
else
  PYTHON=python3
  PIP=pip3
fi

info "Installing: fastapi, uvicorn, requests, syncedlyrics, yt-dlp..."
info "This may take 1-3 minutes on first run..."

# Install with visible progress (no -q flag)
if [ "$OS" = "termux" ]; then
  $PYTHON -m pip install -r backend/requirements.txt 2>&1 | tail -5
else
  $PIP install --break-system-packages -r backend/requirements.txt 2>&1 | tail -5
fi

if $PYTHON -c "import fastapi, uvicorn, yt_dlp, syncedlyrics" 2>/dev/null; then
  ok "All Python packages installed"
else
  $PIP install --break-system-packages fastapi uvicorn requests syncedlyrics yt-dlp 2>&1 | tail -3
  if $PYTHON -c "import fastapi" 2>/dev/null; then
    ok "Python packages installed"
  else
    fail "Python packages failed to install. Try: $PIP install -r backend/requirements.txt"
  fi
fi

# ── 3. Node.js Frontend Dependencies ──
step "3/5  Installing Frontend (npm) Packages"

info "Installing Next.js, React, and dependencies..."
if [ -d "node_modules" ]; then
  ok "node_modules already exists — skipping npm install"
else
  npm install 2>&1 | tail -1 >/dev/null &
  PID=$!
  spinner $PID "npm install (this may take a minute)..."
  wait $PID 2>/dev/null || true

  if [ -d "node_modules/.bin/next" ] || [ -f "node_modules/.bin/next" ]; then
    ok "Frontend dependencies installed"
  else
    npm install 2>&1 | tail -5
    if [ -d "node_modules" ]; then
      ok "Frontend dependencies installed"
    else
      fail "npm install failed. Check your internet connection."
    fi
  fi
fi

# ── 4. Create Downloads Folder ──
step "4/5  Setting Up Local Storage"

mkdir -p backend/downloads
ok "Downloads folder ready: backend/downloads/"

# ── 5. Build Frontend ──
step "5/5  Building Frontend"

if [ -d ".next" ]; then
  info "Existing build found — rebuilding..."
fi

npx next build 2>&1 | tail -3 &
PID=$!
spinner $PID "Building Sonic Player (this may take a while)..."
wait $PID 2>/dev/null || true

if [ -d ".next" ]; then
  ok "Build complete! ✓"
else
  warn "Build failed. You can run 'npm run build' manually later."
fi

# ── Done ──
echo ""
echo -e "  ${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "  ${GREEN}║${NC}  🎵 ${BOLD}Sonic Player is ready!${NC}         ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}                                     ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}  Run:  ${CYAN}./start.sh${NC}                   ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}        or                           ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}        ${CYAN}sh start.sh${NC}                    ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}                                     ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}  📱  Frontend → http://localhost:3004 ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}  ⚙️   Backend  → http://localhost:8005 ${GREEN}║${NC}"
echo -e "  ${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
