import threading
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime
from data.cache.preloader import DataPreloader, PRICE_UPDATE_LOG


class PriceUpdater:
    """Belirli araliklarla fiyat guncelleyen arka plan servisi."""

    def __init__(self, interval_minutes: int = 15, backup_enabled: bool = True):
        self.interval_seconds = interval_minutes * 60
        self.backup_enabled = backup_enabled
        self._running = False
        self._thread = None
        self._last_update = None
        self._update_count = 0
        self._error_count = 0
        self._loader = DataPreloader()

    def start(self):
        """Fiyat guncelleme servisini baslatir."""
        if self._running:
            print("[PriceUpdater] Zaten calisiyor.")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        msg = f"[PriceUpdater] Baslatildi. Her {self.interval_seconds // 60} dk'da bir guncellenecek."
        print(msg)
        self._log(msg)

    def stop(self):
        """Fiyat guncelleme servisini durdurur."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        msg = "[PriceUpdater] Durduruldu."
        print(msg)
        self._log(msg)

    def _run_loop(self):
        """Ana guncelleme dongusu."""
        while self._running:
            try:
                self._do_update()
            except Exception as e:
                self._error_count += 1
                self._log(f"Guncelleme hatasi: {e}")
                print(f"[PriceUpdater] Hata: {e}")

            # Belirlenen aralik kadar bekle (her 5 sn'de bir kontrol et ki hemen durdurulabilsin)
            elapsed = 0
            while self._running and elapsed < self.interval_seconds:
                time.sleep(5)
                elapsed += 5

    def _do_update(self):
        """Tek bir guncelleme islemi yapar."""
        now = datetime.now()
        msg = f"Fiyat guncellemesi basliyor ({now.strftime('%H:%M:%S')})"
        print(f"[PriceUpdater] {msg}")
        self._log(msg)

        # Backup al (eger aciksa)
        if self.backup_enabled:
            self._loader.backup_data()

        # Sadece fiyat guncelle
        self._loader.update_prices_only()

        self._last_update = datetime.now()
        self._update_count += 1

        msg = f"Guncelleme tamamlandi (Toplam: {self._update_count} guncelleme, {self._error_count} hata)"
        print(f"[PriceUpdater] {msg}")
        self._log(msg)

    def force_update(self):
        """Manuel olarak hemen guncelleme yapar."""
        msg = "Manuel guncelleme baslatildi"
        print(f"[PriceUpdater] {msg}")
        self._log(msg)

        if self.backup_enabled:
            self._loader.backup_data()

        self._loader.update_prices_only()
        self._last_update = datetime.now()
        self._update_count += 1

        msg = "Manuel guncelleme tamamlandi"
        print(f"[PriceUpdater] {msg}")
        self._log(msg)
        return self._loader.get_all_data()

    def get_status(self) -> dict:
        """Servis durumunu dondurur."""
        return {
            "running": self._running,
            "interval_minutes": self.interval_seconds // 60,
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "total_updates": self._update_count,
            "total_errors": self._error_count,
            "backup_enabled": self.backup_enabled,
        }

    def _log(self, message: str):
        """Log dosyasina yazar."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(PRICE_UPDATE_LOG, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass


if __name__ == "__main__":
    updater = PriceUpdater(interval_minutes=15, backup_enabled=True)
    updater.start()

    print("Fiyat guncelleme servisi calisiyor. Durdurmak icin Ctrl+C basin.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        updater.stop()
        print("Durduruldu.")
