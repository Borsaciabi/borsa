#!/bin/bash
# ============================================
# BIST Hisse Analiz Platformu - VPS Kurulum
# Ubuntu 20.04+ / Debian 11+ icin
# ============================================
# Kullanim:
#   chmod +x setup_vps.sh
#   sudo ./setup_vps.sh
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
    echo -e "${GREEN}     VPS Kurulum${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
}

print_step() {
    echo -e "${BLUE}[$1/$2]${NC} ${YELLOW}$3${NC}"
}

print_ok() {
    echo -e "${GREEN}  ✓ $1${NC}"
}

print_error() {
    echo -e "${RED}  ✗ $1${NC}"
}

# Root kontrol
if [[ $EUID -ne 0 ]]; then
    print_error "Bu script root olarak calistirilmali: sudo ./setup_vps.sh"
    exit 1
fi

print_header

# Kullanici adi
KULLANICI="borsa"
PROJE_DIR="/home/$KULLANICI/borsa"
PYTHON_VERSION="3.11"

echo -e "${YELLOW}Kurulum basliyor...${NC}"
echo ""

# ============================================
# Adim 1: Guncelleme
# ============================================
print_step 1 8 "Sistem guncelleniyor..."
apt update -qq > /dev/null 2>&1
apt upgrade -y -qq > /dev/null 2>&1
print_ok "Sistem guncellendi"

# ============================================
# Adim 2: Gerekli paketler
# ============================================
print_step 2 8 "Gerekli paketler kuruluyor..."
apt install -y -qq \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv \
    python${PYTHON_VERSION}-dev \
    python3-pip \
    git \
    curl \
    wget \
    nginx \
    > /dev/null 2>&1
print_ok "Paketler kuruldu"

# ============================================
# Adim 3: Kullanici olusturma
# ============================================
print_step 3 8 "Kullanici olusturuluyor..."
if ! id "$KULLANICI" &>/dev/null; then
    adduser --disabled-password --gecos "" $KULLANICI
    usermod -aG sudo $KULLANICI
    print_ok "Kullanici olusturuldu: $KULLANICI"
else
    print_ok "Kullanici zaten mevcut: $KULLANICI"
fi

# ============================================
# Adim 4: Proje dizini
# ============================================
print_step 4 8 "Proje dizini olusturuluyor..."
sudo -u $KULLANICI mkdir -p $PROJE_DIR
print_ok "Proje dizini: $PROJE_DIR"

# ============================================
# Adim 5: Python virtual environment
# ============================================
print_step 5 8 "Python virtual environment olusturuluyor..."
sudo -u $KULLANICI python${PYTHON_VERSION} -m venv $PROJE_DIR/venv
print_ok "Virtual environment olusturuldu"

# ============================================
# Adim 6: Kutuphane kurulumu
# ============================================
print_step 6 8 "Kutuphaneler yukleniyor (2-5 dk surebilir)..."
sudo -u $KULLANICI $PROJE_DIR/venv/bin/pip install --upgrade pip -q
sudo -u $KULLANICI $PROJE_DIR/venv/bin/pip install -r /dev/stdin << 'EOF'
# Veri Kutuphaneleri
yfinance>=0.2.30

# Backend
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
gunicorn>=21.2.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6

# Telegram Bot
python-telegram-bot>=22.8

# Web Scraping
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
httpx>=0.26.0

# Veri Islem
pandas>=2.0.0
numpy>=1.24.0

# Dashboard
streamlit>=1.30.0
plotly>=5.18.0

# Raporlama
openpyxl>=3.1.0
fpdf2>=2.7.0

# Araclar
python-dotenv>=1.0.0
EOF
print_ok "Kutuphaneler yuklendi"

# ============================================
# Adim 7: .env dosyasi
# ============================================
print_step 7 8 ".env dosyasi olusturuluyor..."
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "dev-secret-key-change-me-in-production")
sudo -u $KULLANICI tee $PROJE_DIR/.env > /dev/null << EOF
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

# ============================================
# Adim 8: Systemd servisi
# ============================================
print_step 8 8 "Systemd servisi olusturuluyor..."
tee /etc/systemd/system/borsa.service > /dev/null << EOF
[Unit]
Description=BIST Borsa Analiz Platformu
After=network.target

[Service]
Type=simple
User=$KULLANICI
Group=$KULLANICI
WorkingDirectory=$PROJE_DIR
ExecStart=$PROJE_DIR/venv/bin/python run_all.py
Restart=always
RestartSec=10
Environment=PYTHONPATH=$PROJE_DIR

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable borsa > /dev/null 2>&1
print_ok "Systemd servisi olusturuldu"

# ============================================
# Nginx yapılandırması (opsiyonel)
# ============================================
echo ""
echo -e "${YELLOW}Nginx reverse proxy ayarlaniyor...${NC}"
tee /etc/nginx/sites-available/borsa > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    # Dashboard
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # API Docs
    location /docs {
        proxy_pass http://127.0.0.1:8000;
    }
    location /openapi.json {
        proxy_pass http://127.0.0.1:8000;
    }
}
EOF

ln -sf /etc/nginx/sites-available/borsa /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t > /dev/null 2>&1 && systemctl reload nginx
print_ok "Nginx ayarlandi"

# ============================================
# Basari mesaji
# ============================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}     KURULUM TAMAMLANDI!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "  ${BLUE}Proje dizini:${NC}  $PROJE_DIR"
echo -e "  ${BLUE}Kullanici:${NC}     $KULLANICI"
echo -e "  ${BLUE}Python:${NC}        $PYTHON_VERSION"
echo -e "  ${BLUE}Virtual Env:${NC}   $PROJE_DIR/venv"
echo ""
echo -e "  ${YELLOW}Adim 1:${NC} Projeyi yukleyin:"
echo -e "    sudo -u $KULLANICI cp -r /path/to/Python\\ Borsa/* $PROJE_DIR/"
echo -e "    sudo -u $KULLANICI cp -r /path/to/Python\\ Borsa/.env* $PROJE_DIR/"
echo ""
echo -e "  ${YELLOW}Adim 2:${NC} Veritabanini baslatin:"
echo -e "    sudo -u $KULLANICI $PROJE_DIR/venv/bin/python -c \"from data.database.models import init_db; init_db()\""
echo ""
echo -e "  ${YELLOW}Adim 3:${NC} Servisi baslatin:"
echo -e "    sudo systemctl start borsa"
echo ""
echo -e "  ${YELLOW}Adim 4:${NC} Erisim:"
echo -e "    Dashboard:  http://SUNUCU-IP"
echo -e "    API:        http://SUNUCU-IP/api/"
echo -e "    API Docs:   http://SUNUCU-IP/docs"
echo ""
echo -e "  ${YELLOW}Yonetim:${NC}"
echo -e "    Durum:      sudo systemctl status borsa"
echo -e "    Durdur:     sudo systemctl stop borsa"
echo -e "    Yeniden:    sudo systemctl restart borsa"
echo -e "    Loglar:     sudo journalctl -u borsa -f"
echo ""
