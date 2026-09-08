import subprocess
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# PriceUpdater'i baslat
from data.cache.price_updater import PriceUpdater
from config.settings import PRICE_UPDATE_MINUTES, BACKUP_ENABLED

updater = PriceUpdater(interval_minutes=PRICE_UPDATE_MINUTES, backup_enabled=BACKUP_ENABLED)

print("Python Borsa baslatiliyor...")
print()

# API'yi baslat
print("[1/3] FastAPI baslatiliyor (port 8000)...")
api_proc = subprocess.Popen(
    [sys.executable, "run_api.py"],
    cwd=os.getcwd(),
)

# Streamlit'i baslat
print("[2/3] Streamlit baslatiliyor (port 8501)...")
streamlit_proc = subprocess.Popen(
    [sys.executable, "-m", "streamlit", "run", "web/streamlit_app.py",
     "--server.port", "8501"],
    cwd=os.getcwd(),
)

# Telegram botunu baslat
telegram_proc = None
from config.settings import TELEGRAM_BOT_TOKEN
if TELEGRAM_BOT_TOKEN:
    print("[3/4] Telegram bot baslatiliyor...")
    telegram_proc = subprocess.Popen(
        [sys.executable, "run_bot.py"],
        cwd=os.getcwd(),
    )
else:
    print("[3/4] Telegram bot atlandi: TELEGRAM_BOT_TOKEN ayarlanmamis.")

# Fiyat guncelleme servisini baslat
print(f"[4/4] Fiyat guncelleme baslatiliyor (her {PRICE_UPDATE_MINUTES} dk)...")
updater.start()

print()
print("Tum servisler baslatildi!")
print("  API:        http://localhost:8000")
print("  Dashboard:  http://localhost:8501")
print("  API Docs:   http://localhost:8000/docs")
print(f"  Fiyat Guncelleme: Her {PRICE_UPDATE_MINUTES} dk (Mynet)")
print()
print("Durdurmak icin Ctrl+C basin.")

try:
    api_proc.wait()
    streamlit_proc.wait()
except KeyboardInterrupt:
    print("\nDurduruluyor...")
    updater.stop()
    api_proc.terminate()
    streamlit_proc.terminate()
    if telegram_proc:
        telegram_proc.terminate()
