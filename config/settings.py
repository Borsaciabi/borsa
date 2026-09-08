import os
from pathlib import Path
from dotenv import load_dotenv

# PythonAnywhere ve normal ortam icin BASE_DIR
if os.getenv("PYTHONANYWHERE_DOMAIN"):
    BASE_DIR = Path("/home/hayatadair/borsa")
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

DATABASE_DIR = BASE_DIR / "data"
DATABASE_DIR.mkdir(exist_ok=True)
DATABASE_PATH = DATABASE_DIR / "borsa.db"

CACHE_DIR = BASE_DIR / "data" / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))

RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

# Fiyat Guncelleme
PRICE_UPDATE_MINUTES = int(os.getenv("PRICE_UPDATE_MINUTES", "15"))
BACKUP_ENABLED = os.getenv("BACKUP_ENABLED", "true").lower() == "true"
