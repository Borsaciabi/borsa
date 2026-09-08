import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from data.cache.price_updater import PriceUpdater
from config.settings import PRICE_UPDATE_MINUTES, BACKUP_ENABLED

# PriceUpdater'i baslat
updater = PriceUpdater(interval_minutes=PRICE_UPDATE_MINUTES, backup_enabled=BACKUP_ENABLED)
updater.start()
print(f"[PriceUpdater] Baslatildi - Her {PRICE_UPDATE_MINUTES} dk'da bir fiyat guncellenecek")

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)
