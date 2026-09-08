"""
PythonAnywhere Always-on Task (Hacker Plan Gerekli)
Her 15 dakikada bir Mynet'ten fiyat cekip stock_data.json'i gunceller.

NOT: Bu script sadece PythonAnywhere Hacker planinda ($5/ay) calisir.
Free plan'da Always-on task desteklenmez.

Kullanim (Hacker planinda):
  Dashboard > Tasks > Add new task
  Command: /home/hayatadair/borsa/venv/bin/python /home/hayatadair/borsa/price_updater_task.py
  Schedule: Always
"""

import sys
import os
import time

# Proje dizinini path'e ekle
project_home = '/home/hayatadair/borsa'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.chdir(project_home)

from datetime import datetime
from data.cache.preloader import DataPreloader, PRICE_UPDATE_LOG
from config.settings import PRICE_UPDATE_MINUTES, BACKUP_ENABLED


def log(message: str):
    """Log dosyasina yazar."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}\n"
    print(line.strip())
    try:
        with open(PRICE_UPDATE_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def main():
    """Ana guncelleme dongusu."""
    log("=" * 50)
    log("Price Updater Task baslatildi")
    log(f"Guncelleme araligi: {PRICE_UPDATE_MINUTES} dakika")
    log(f"Backup: {'Acik' if BACKUP_ENABLED else 'Kapali'}")
    log("=" * 50)

    loader = DataPreloader()
    update_count = 0
    error_count = 0

    while True:
        try:
            now = datetime.now()
            log(f"Guncelleme basliyor... ({now.strftime('%H:%M:%S')})")

            # Backup al
            if BACKUP_ENABLED:
                loader.backup_data()

            # Sadece fiyat guncelle
            loader.update_prices_only()

            update_count += 1
            log(f"Guncelleme tamamlandi (Toplam: {update_count})")

        except Exception as e:
            error_count += 1
            log(f"HATA: {e} (Toplam hata: {error_count})")

            # Hata durumunda cache'i yuklemeyi dene
            try:
                loader.load_cache_with_backup()
                log("Backup'tan yukleme basarili")
            except Exception as backup_error:
                log(f"Backup yukleme hatasi: {backup_error}")

        # Bir sonraki guncellemeye kadar bekle
        sleep_seconds = PRICE_UPDATE_MINUTES * 60
        log(f"Siradaki guncelleme: {sleep_seconds // 60} dakika sonra")
        log("-" * 30)

        time.sleep(sleep_seconds)


if __name__ == "__main__":
    main()
