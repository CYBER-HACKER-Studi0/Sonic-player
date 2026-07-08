#!/data/data/com.termux/files/usr/bin/bash
# ═══════════════════════════════════════════════════════════
# Sonic Player — Termux One-Click Setup
# Installs everything: pkg packages, yt-dlp, git clone, npm, build
# ═══════════════════════════════════════════════════════════

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
PURPLE='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

print_banner() {
  echo ""
  echo -e "  ${PURPLE}╔══════════════════════════════════════╗${NC}"
  echo -e "  ${PURPLE}║${NC}  ${BOLD}🎵 Sonic Player — Termux Setup${NC}  ${PURPLE}║${NC}"
  echo -e "  ${PURPLE}║${NC}  by CYBER-HACKER-Studio           ${PURPLE}║${NC}"
  echo -e "  ${PURPLE}╚══════════════════════════════════════╝${NC}"
  echo ""
  echo -e "  ${YELLOW}⚠ Requires: Termux + 500MB free + stable internet${NC}"
  echo ""
}

step()   { echo -e "\n  ${GREEN}━━━${NC} ${BOLD}$1${NC}"; }
info()   { echo -e "  ${CYAN}→${NC} $1"; }
ok()     { echo -e "  ${GREEN}✓${NC} $1"; }
warn()   { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail()   { echo -e "  ${RED}✗${NC} $1"; }

# ── Check Termux ──
if [ -z "$TERMUX_VERSION" ]; then
  echo -e "\n  ${RED}✗ This script only runs on Termux${NC}"
  echo -e "  ${RED}   Install Termux from F-Droid first${NC}\n"
  exit 1
fi

# ── Storage permission (one-time) ──
termux-setup-storage 2>/dev/null || true
sleep 1

# ── 1. Update Termux ──
print_banner
step "1/7  Updating Termux"

info "Updating package lists..."
yes | pkg update 2>&1 | tail -2

# Fix any broken packages before upgrade
info "Fixing broken packages..."
apt --fix-broken install -y 2>/dev/null || true
dpkg --configure -a 2>/dev/null || true

info "Upgrading packages (this may take a while)..."
yes | pkg upgrade -y 2>&1 | tail -2
if [ $? -ne 0 ]; then
  warn "Upgrade failed — retrying with fix..."
  apt --fix-broken install -y 2>/dev/null
  dpkg --configure -a 2>/dev/null
  yes | pkg upgrade -y 2>&1 | tail -2 || true
fi
ok "Termux is up to date ✓"

# ── 2. Install base packages ──
step "2/7  Installing Base Packages"

PACKAGES="python nodejs ffmpeg git curl"
for pkg in $PACKAGES; do
  if command -v "$pkg" &>/dev/null; then
    ok "$pkg already installed"
  else
    info "Installing $pkg..."
    apt-get install -y "$pkg" 2>&1 | tail -1 || {
      warn "$pkg failed — retrying..."
      apt-get install -y "$pkg" 2>&1 | tail -1 || true
    }
  fi
done

# Verify ffmpeg works
if command -v ffmpeg &>/dev/null; then
  ok "ffmpeg $(ffmpeg -version 2>&1 | head -1 | grep -oP 'version \K[^ ]+' || echo '✓')"
else
  warn "ffmpeg broken — reinstalling..."
  apt-get remove -y ffmpeg 2>/dev/null || true
  apt-get autoremove -y 2>/dev/null || true
  apt-get install -y ffmpeg 2>&1 | tail -1 || true
fi

# ── 3. Install yt-dlp ──
step "3/7  Installing yt-dlp"

if command -v yt-dlp &>/dev/null; then
  VER=$(yt-dlp --version 2>/dev/null | head -1)
  ok "yt-dlp already installed ($VER)"
else
  info "Installing yt-dlp..."
  # Method 1: pkg
  apt-get install -y yt-dlp 2>&1 | tail -1 || \
  # Method 2: pip
  pip install yt-dlp 2>&1 | tail -1 || true
  
  if command -v yt-dlp &>/dev/null; then
    ok "yt-dlp installed ✓"
  else
    warn "yt-dlp install failed. Try later: pkg install yt-dlp"
  fi
fi

# ── 4. Clone project ──
step "4/7  Downloading Sonic Player"

if [ -d "Sonic-player" ]; then
  info "Project exists — updating..."
  cd Sonic-player
  git pull 2>&1 | tail -1
else
  info "Cloning repository..."
  git clone https://github.com/CYBER-HACKER-Studi0/Sonic-player.git 2>&1 | tail -1
  cd Sonic-player
fi
ok "Project ready ✓"

# ── 5. Install npm packages ──
step "5/7  Installing Frontend (npm)"

if [ ! -d "node_modules" ]; then
  info "Installing dependencies..."
  npm install 2>&1 | tail -3
  if [ -d "node_modules" ]; then
    ok "npm packages installed ✓"
  else
    warn "npm install failed — retrying with --legacy-peer-deps"
    npm install --legacy-peer-deps 2>&1 | tail -3
  fi
else
  ok "node_modules exists"
fi

# ── 6. Build ──
step "6/7  Building Frontend"

info "Running next build..."
npx next build 2>&1 | tail -3
if [ -d ".next" ]; then
  ok "Build complete ✓"
else
  warn "Build failed — run manually: npx next dev -p 3004"
fi

# ── 7. Downloads folder ──
mkdir -p backend/downloads
ok "Downloads folder ready ✓"

# ── Done ──
echo ""
echo -e "  ${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "  ${GREEN}║${NC}  🎵 ${BOLD}Sonic Player is ready!${NC}         ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}                                     ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}  Start with:                         ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}  ${CYAN}sh start.sh${NC}                       ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}                                     ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}  🌐  Frontend → http://localhost:3004 ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}  ⚙️   Backend  → http://localhost:8005 ${GREEN}║${NC}"
echo -e "  ${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
