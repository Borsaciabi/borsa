#!/bin/bash
# ============================================
# BIST Hisse Analiz Platformu - PythonAnywhere Kurulum
# PythonAnywhere Bash Console icin
# ============================================
# Kullanim:
#   1. PythonAnywhere'de Bash console ac
#   2. Bu dosyayi yukle veya icerigi yapistir
#   3. chmod +x setup_pa.sh && ./setup_pa.sh
# ============================================

set -e

# Renkler
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}     BIST Hisse Analiz Platformu${NC}"
    echo -e "${GREEN}     PythonAnywhere Kurulum${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}[$1/$2]${NC} ${YELLOW}$3${NC}"
}

print_ok() {
    echo -e "${GREEN}  ✓ $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}  ⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}  ✗ $1${NC}"
}

print_header

# Kullanici adi otomatik algila
KULLANICI=$(whoami)
PROJE_DIR="/home/$KULLANICI/borsa"

echo -e "  Kullanici: ${BLUE}$KULLANICI${NC}"
echo -e "  Proje:     ${BLUE}$PROJE_DIR${NC}"
echo ""

# ============================================
# Adim 1: Proje dizini kontrol
# ============================================
print_step 1 6 "Proje dizini kontrol ediliyor..."
if [ ! -d "$PROJE_DIR" ]; then
    print_warn "Proje dizini yok, olusturuluyor..."
    mkdir -p $PROJE_DIR
fi
print_ok "Proje dizini hazir"

# ============================================
# Adim 2: Git ile proje yukleme (eger yoksa)
# ============================================
print_step 2 6 "Proje dosyalari kontrol ediliyor..."
if [ ! -f "$PROJE_DIR/app.py" ]; then
    print_warn "Proje dosyalari bulunamadi!"
    echo ""
    echo -e "  ${YELLOW}Manuel olarak projeyi yukleyin:${NC}"
    echo -e "  1. Dashboard > Files > Upload files"
    echo -e "  2. Tum proje dosyalarini /home/$KULLANICI/borsa/ dizinine yukleyin"
    echo -e "  3. Veya git ile yukleyin:"
    echo -e "     cd $PROJE_DIR && git clone <repo-url> ."
    echo ""
    echo -e "  ${YELLOW}Devam etmek icin Enter'a basin...${NC}"
    read -p ""
else
    print_ok "Proje dosyalari mevcut"
fi

# ============================================
# Adim 3: Virtual environment
# ============================================
print_step 3 6 "Virtual environment olusturuluyor..."
if [ ! -d "$PROJE_DIR/venv" ]; then
    python3.10 -m venv $PROJE_DIR/venv
    print_ok "Virtual environment olusturuldu"
else
    print_ok "Virtual environment zaten mevcut"
fi

# ============================================
# Adim 4: Kutuphane kurulumu
# ============================================
print_step 4 6 "Kutuphaneler yukleniyor (2-5 dk surebilir)..."
source $PROJE_DIR/venv/bin/activate
pip install --upgrade pip -q 2>/dev/null
pip install -q -r $PROJE_DIR/requirements.txt 2>/dev/null
print_ok "Kutuphaneler yuklendi"

# ============================================
# Adim 5: .env dosyasi
# ============================================
print_step 5 6 ".env dosyasi olusturuluyor..."
if [ ! -f "$PROJE_DIR/.env" ]; then
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "dev-secret-key-change-me")
    cat > $PROJE_DIR/.env << EOF
# JWT
JWT_SECRET_KEY=$JWT_SECRET
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Telegram Bot
TELEGRAM_BOT_TOKEN=

# Database
DATABASE_URL=sqlite:///$PROJE_DIR/data/borsa.db

# Cache
CACHE_TTL_SECONDS=300

# API Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Fiyat Guncelleme
PRICE_UPDATE_MINUTES=15
BACKUP_ENABLED=true
EOF
    print_ok ".env olusturuldu (JWT_SECRET otomatik uretildi)"
else
    print_ok ".env zaten mevcut"
fi

# ============================================
# Adim 6: Veritabani baslatma
# ============================================
print_step 6 6 "Veritabani baslatiliyor..."
cd $PROJE_DIR
mkdir -p data/cache
python3 -c "from data.database.models import init_db; init_db()" 2>/dev/null
print_ok "Veritabani hazir"

# ============================================
# WSGI dosyasi olusturma
# ============================================
echo ""
echo -e "${YELLOW}WSGI dosyasi olusturuluyor...${NC}"
cat > $PROJE_DIR/wsgi.py << 'WSGIEOF'
import sys
import os

project_home = '/home/hayatadair/borsa'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.chdir(project_home)

from app import app as application
WSGIEOF

# Kullanici adini guncelle
sed -i "s/hayatadair/$KULLANICI/g" $PROJE_DIR/wsgi.py
print_ok "WSGI dosyasi olusturuldu"

# ============================================
# Fiyat guncelleme task'i
# ============================================
echo -e "${YELLOW}Always-on task dosyasi hazirlaniyor...${NC}"
cat > $PROJE_DIR/price_updater_task.py << 'TASKEOF'
import sys
import os
import time

project_home = '/home/hayatadair/borsa'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.chdir(project_home)

from datetime import datetime
from data.cache.preloader import DataPreloader, PRICE_UPDATE_LOG
from config.settings import PRICE_UPDATE_MINUTES, BACKUP_ENABLED

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}\n"
    print(line.strip())
    try:
        with open(PRICE_UPDATE_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except:
        pass

def main():
    log("Price Updater baslatildi")
    loader = DataPreloader()
    update_count = 0
    while True:
        try:
            if BACKUP_ENABLED:
                loader.backup_data()
            loader.update_prices_only()
            update_count += 1
            log(f"Guncelleme tamamlandi (Toplam: {update_count})")
        except Exception as e:
            log(f"HATA: {e}")
        time.sleep(PRICE_UPDATE_MINUTES * 60)

if __name__ == "__main__":
    main()
TASKEOF

sed -i "s/hayatadair/$KULLANICI/g" $PROJE_DIR/price_updater_task.py
print_ok "Always-on task hazir"

# ============================================
# Basari mesaji
# ============================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}     KURULUM TAMAMLANDI!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "  ${BLUE}Proje dizini:${NC} $PROJE_DIR"
echo -e "  ${BLUE}Kullanici:${NC}    $KULLANICI"
echo ""
echo -e "  ${YELLOW}SIMDI MANUEL ADIMLARI YAPIN:${NC}"
echo ""
echo -e "  ${GREEN}Adim 1:${NC} WSGI Yapilandir"
echo -e "    1. Dashboard > Web > WSGI configuration file tikla"
echo -e "    2. Tum icerigi sil"
echo -e "    3. Asagidaki dosyanin icerigini yapistir:"
echo -e "       cat $PROJE_DIR/wsgi.py"
echo ""
echo -e "  ${GREEN}Adim 2:${NC} Web Uygulamasi Olustur"
echo -e "    1. Dashboard > Web > Add a new web app tikla"
echo -e "    2. Manual configuration > Python 3.10 sec"
echo -e "    3. Source code: $PROJE_DIR"
echo -e "    4. Working directory: $PROJE_DIR"
echo -e "    5. WSGI: $PROJE_DIR/wsgi.py"
echo -e "    6. Virtualenv: $PROJE_DIR/venv"
echo -e "    7. Reload butonuna bas"
echo ""
echo -e "  ${GREEN}Adim 3:${NC} Always-on Task Ekle (Hacker planinda)"
echo -e "    1. Dashboard > Tasks > Add new task tikla"
echo -e "    2. Command: $PROJE_DIR/venv/bin/python $PROJE_DIR/price_updater_task.py"
echo -e "    3. Schedule: Always sec"
echo -e "    4. Run ile test et"
echo ""
echo -e "  ${GREEN}Adim 4:${NC} Test Et"
echo -e "    https://$KULLANICI.pythonanywhere.com"
echo ""
echo -e "  ${YELLOW}Dosya yollari:${NC}"
echo -e "    WSGI:  $PROJE_DIR/wsgi.py"
echo -e "    Task:  $PROJE_DIR/price_updater_task.py"
echo -e "    .env:  $PROJE_DIR/.env"
echo -e "    DB:    $PROJE_DIR/data/borsa.db"
echo -e "    Cache: $PROJE_DIR/data/cache/stock_data.json"
echo ""
