#!/data/data/com.termux/files/usr/bin/bash
# ═══════════════════════════════════════════════════════════
# Sonic Player — Termux Full Installation Script
# من أول تثبيت Termux للتحديثات للتشغيل
# ═══════════════════════════════════════════════════════════

# من غير set -e عشان نتعامل مع الأخطاء بنفسنا

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
  echo -e "  ${YELLOW}⚠  تأكد إنك شغال على Termux${NC}"
  echo -e "  ${YELLOW}   مساحة تخزين فارغة: 500MB+${NC}"
  echo -e "  ${YELLOW}   نت مستقر (فيش او واي فاي)${NC}"
  echo ""
}

step()   { echo -e "\n  ${GREEN}━━━${NC} ${BOLD}$1${NC}"; }
info()   { echo -e "  ${CYAN}→${NC} $1"; }
ok()     { echo -e "  ${GREEN}✓${NC} $1"; }
warn()   { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail()   { echo -e "  ${RED}✗${NC} $1"; }

# ── التحقق من Termux ──
if [ -z "$TERMUX_VERSION" ]; then
  echo -e "\n  ${RED}✗✗✗ مش عارف أexecute الـ script ده غير على Termux${NC}"
  echo -e "  ${RED}   روح نزل Termux من F-Droid الأول${NC}\n"
  exit 1
fi

# ── منح صلاحيات التخزين (مرة واحدة) ──
termux-setup-storage 2>/dev/null || true
sleep 1

# ── 1. تحديث Termux ──
print_banner
step "1/7  تحديث Termux"

info "بحدث الحزم..."
yes | pkg update 2>&1 | tail -2

# إصلاح أي حزم مكسورة قبل الـ upgrade
info "بصلح أي حزم مكسورة..."
apt --fix-broken install -y 2>/dev/null || true
dpkg --configure -a 2>/dev/null || true

yes | pkg upgrade -y 2>&1 | tail -2
# لو الـ upgrade فشل بسبب حزمة مكسورة، نصلحها ونجرب تاني
if [ $? -ne 0 ]; then
  warn "في مشكلة تحديث — بحاول أصلح..."
  apt --fix-broken install -y 2>/dev/null
  dpkg --configure -a 2>/dev/null
  yes | pkg upgrade -y 2>&1 | tail -2 || true
fi
ok "Termux أخر إصدار ✓"

# ── 2. الحزم الأساسية ──
step "2/7  تثبيت الحزم الأساسية"

PACKAGES="python nodejs ffmpeg git curl"
for pkg in $PACKAGES; do
  if command -v "$pkg" &>/dev/null; then
    ok "$pkg موجود بالفعل"
  else
    info "بتنزيل $pkg..."
    apt-get install -y "$pkg" 2>&1 | tail -1 || {
      warn "$pkg فشل في التثبيت — بحاول مرة تانية"
      apt-get install -y "$pkg" 2>&1 | tail -1 || true
    }
  fi
done

# التأكد إن ffmpeg شغال
if command -v ffmpeg &>/dev/null; then
  ok "ffmpeg $(ffmpeg -version 2>&1 | head -1 | grep -oP 'version \K[^ ]+' || echo '✓')"
else
  warn "ffmpeg مش شغال — ممكن اللينكات القديمة"
  info "بحاول أعيد تثبيت ffmpeg..."
  apt-get remove -y ffmpeg 2>/dev/null || true
  apt-get autoremove -y 2>/dev/null || true
  apt-get install -y ffmpeg 2>&1 | tail -1 || true
fi

# ── 3. تثبيت yt-dlp ──
step "3/7  تثبيت yt-dlp"

if command -v yt-dlp &>/dev/null; then
  VER=$(yt-dlp --version 2>/dev/null | head -1)
  ok "yt-dlp موجود ($VER)"
else
  info "بتنزيل yt-dlp..."
  # طريقة 1: pkg
  apt-get install -y yt-dlp 2>&1 | tail -1 || \
  # طريقة 2: pip
  pip install yt-dlp 2>&1 | tail -1 || true
  
  if command -v yt-dlp &>/dev/null; then
    ok "yt-dlp تم ✓"
  else
    warn "yt-dlp مفيهوش تنزيل — جرب بعدين: pkg install yt-dlp"
  fi
fi

# ── 4. تحميل المشروع ──
step "4/7  تحميل Sonic Player"

if [ -d "Sonic-player" ]; then
  info "المشروع موجود — بتحدث..."
  cd Sonic-player
  git pull 2>&1 | tail -1
else
  info "بتحميل المشروع..."
  git clone https://github.com/CYBER-HACKER-Studi0/Sonic-player.git 2>&1 | tail -1
  cd Sonic-player
fi
ok "المشروع جاهز ✓"

# ── 5. تثبيت npm packages ──
step "5/7  تثبيت حزم الواجهة (npm)"

if [ ! -d "node_modules" ]; then
  info "بتنزيل dependencies..."
  npm install 2>&1 | tail -3
  if [ -d "node_modules" ]; then
    ok "npm packages تم ✓"
  else
    warn "npm install فشل — بحاول بـ --legacy-peer-deps"
    npm install --legacy-peer-deps 2>&1 | tail -3
  fi
else
  ok "node_modules موجود"
fi

# ── 6. Build ──
step "6/7  بناء المشروع"

info "بتبني الواجهة..."
npx next build 2>&1 | tail -3
if [ -d ".next" ]; then
  ok "البناء تم ✓"
else
  warn "البناء فشل — ممكن تشغله بـ: npx next dev -p 3004"
fi

# ── 7. Downloads folder ──
mkdir -p backend/downloads
ok "مجلد التحميلات جاهز ✓"

# ── خلاص ──
echo ""
echo -e "  ${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "  ${GREEN}║${NC}  🎵 ${BOLD}Sonic Player جاهز!${NC}            ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}                                     ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}  شغّل بـ:                            ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}  ${CYAN}sh start.sh${NC}                       ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}                                     ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}  🌐  Frontend → http://localhost:3004 ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}  ⚙️   Backend  → http://localhost:8005 ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}                                     ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}  ${YELLOW}⚠${NC} افتح http://localhost:3004        ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}     على Chrome تلفونك                  ${GREEN}║${NC}"
echo -e "  ${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
