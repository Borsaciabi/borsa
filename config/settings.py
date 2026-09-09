import os
from pathlib import Path
from dotenv import load_dotenv

# PythonAnywhere ve normal ortam icin BASE_DIR
if os.getenv("PYTHONANYWHERE_DOMAIN"):
    BASE_DIR = Path("/home/hayatadair/borsa")
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

env_file = os.getenv("BORSA_ENV_FILE")
if env_file:
    load_dotenv(env_file)
else:
    load_dotenv(BASE_DIR / ".env")
    load_dotenv(Path.home() / "BorsaAnalizData" / ".env", override=False)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Keep local data outside git worktrees so different checkouts share one
# account, portfolio and market database.
if os.getenv("PYTHONANYWHERE_DOMAIN"):
    DATABASE_DIR = BASE_DIR / "data"
else:
    DATABASE_DIR = Path(os.getenv("BORSA_DATA_DIR", Path.home() / "BorsaAnalizData"))
DATABASE_DIR.mkdir(exist_ok=True)
DATABASE_PATH = DATABASE_DIR / "borsa.db"

# Cache follows the same shared data root to avoid repeated full downloads
# when the app is launched from another checkout.
CACHE_DIR = DATABASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))

RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

# Fiyat Guncelleme
PRICE_UPDATE_MINUTES = int(os.getenv("PRICE_UPDATE_MINUTES", "15"))
BACKUP_ENABLED = os.getenv("BACKUP_ENABLED", "true").lower() == "true"
