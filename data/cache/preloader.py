import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import time
from datetime import datetime
from pathlib import Path
from data.fetchers.mynet_fetcher import MynetFetcher
from data.fetchers.yahoo_fetcher import YahooFetcher
from data.fetchers.asenax_fetcher import AsenaxFetcher
from data.fetchers.kap_fetcher import KapFetcher
from data.fetchers.isyatirim_hisse_fetcher import IsYatirimHisseFetcher
from analysis.value_analysis import ValueAnalyzer
from data.database.db_manager import DBManager


CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

CACHE_FILE = CACHE_DIR / "stock_data.json"
CACHE_TIME_FILE = CACHE_DIR / "last_update.txt"
BACKUP_FILE = CACHE_DIR / "stock_data_backup.json"
BACKUP_TIME_FILE = CACHE_DIR / "last_update_backup.txt"
PRICE_UPDATE_LOG = CACHE_DIR / "price_update_log.txt"


class DataPreloader:
    """Program basladiginda tum verileri onceden yukler ve cache'ler."""

    def __init__(self):
        self.mynet = MynetFetcher()
        self.yahoo = YahooFetcher()
        self.asenax = AsenaxFetcher()
        self.kap = KapFetcher()
        self.isyatirim_hisse = IsYatirimHisseFetcher()
        self.va = ValueAnalyzer()
        self.db = DBManager()
        self._all_data = {}

    def load_all(self, symbols: list = None, progress_callback=None):
        """Tum hisse verilerini yukler."""
        if symbols is None:
            # Once mynet'ten tum hisseleri al
            stocks = self.mynet.fetch_all()
            symbols = [s["stock_code"] for s in stocks]
            # Fiyat bilgisini de ekle
            for s in stocks:
                self._all_data[s["stock_code"]] = {
                    "stock_code": s["stock_code"],
                    "company_name": s.get("company_name", ""),
                    "last_price": s.get("last_price", 0),
                    "change_pct": s.get("change_pct", 0),
                    "change_direction": s.get("change_direction", "flat"),
                    "volume": s.get("volume", 0),
                    "sector": s.get("sector", "N/A"),
                }

        # KAP'tan fiili dolasim verisini toplu al
        print("KAP'tan fiili dolasim verileri cekiliyor...")
        kap_all = self.kap.fetch_all()
        kap_dict = {item["stock_code"]: item for item in kap_all}
        if kap_dict:
            # KAP is the authoritative BIST share universe for this dataset.
            # Do not keep symbols returned by other providers but absent from KAP.
            self._all_data = {
                code: item for code, item in self._all_data.items() if code in kap_dict
            }
            for code, item in kap_dict.items():
                self._all_data.setdefault(code, {
                    "stock_code": code,
                    "company_name": item.get("company_name", ""),
                    "last_price": 0,
                    "change_pct": 0,
                    "volume": 0,
                    "sector": "N/A",
                })
        for code, item in kap_dict.items():
            if code in self._all_data:
                if item.get("company_name"):
                    self._all_data[code]["company_name"] = item["company_name"]
                self._all_data[code]["float_rate"] = item.get("floating_ratio_pct", 0)
                self._all_data[code]["floating_shares"] = item.get("floating_shares", 0)
                self._all_data[code]["float_data_source"] = self.kap.URL
                # KAP'tan toplam hisseyi hesapla: floating_shares / (float_rate / 100)
                fr = item.get("floating_ratio_pct", 0) or 0
                fs = item.get("floating_shares", 0) or 0
                if fr > 0 and fs > 0:
                    total = fs / (fr / 100)
                    self._all_data[code]["total_shares"] = int(total)
                    # Piyasa degerini hesapla: fiyat * toplam hisse
                    price = self._all_data[code].get("last_price", 0) or 0
                    if price > 0:
                        mcap_tl = price * total
                        self._all_data[code]["market_cap"] = mcap_tl
                        self._all_data[code]["market_cap_mn"] = mcap_tl / 1e6

        # Asenax ile piyasa degeri, net borc, F/K, PD/DD (HIZLI API)
        print("Asenax ile temel veriler cekiliyor...")
        asenax_data = self.asenax.tumunu_cek(progress_callback=progress_callback)
        for code, veri in asenax_data.items():
            if code in self._all_data:
                piyasa = veri.get('piyasa_degeri', 0)
                net_kar = veri.get('net_kar', 0)
                fk = veri.get('fiyat_kazanc', 0)
                oz_sermaye = veri.get('oz_sermaye', 0)
                sermaye = veri.get('sermaye', 0)

                if piyasa > 0:
                    self._all_data[code]["market_cap"] = piyasa
                    self._all_data[code]["market_cap_mn"] = piyasa / 1e6
                if sermaye > 0:
                    self._all_data[code]["total_shares"] = sermaye
                if fk > 0:
                    self._all_data[code]["pe"] = fk
                if oz_sermaye > 0 and piyasa > 0:
                    self._all_data[code]["pb"] = piyasa / oz_sermaye if oz_sermaye else 0

        # IsYatirimHisse finansal tablo ve tarihsel veri entegrasyonu.
        # Kutuphane kullanilamazsa mevcut kaynaklar calismaya devam eder.
        if self.isyatirim_hisse.available:
            print("isyatirimhisse ile tarihsel fiyat ve finansal tablolar cekiliyor...")
            try:
                library_data = self.isyatirim_hisse.fetch_and_extract(symbols)
                for code, values in library_data.items():
                    if code not in self._all_data:
                        continue
                    item = self._all_data[code]
                    for key in ("last_price", "market_cap", "market_cap_mn", "total_shares"):
                        if values.get(key):
                            item[key] = values[key]
                    if values.get("net_debt") is not None:
                        item["net_debt"] = values["net_debt"]
                        item["net_debt_mn"] = values.get("net_debt_mn", values["net_debt"] / 1e6)
                    for key in ("pe", "pb", "eps", "revenue", "net_income", "total_equity"):
                        if values.get(key) is not None:
                            item[key] = values[key]
            except Exception as e:
                print(f"isyatirimhisse entegrasyonu basarisiz, mevcut kaynaklara donuluyor: {e}")

        # Is Yatirim'dan TUM HISSELER icin net borc cek (PARALEL - 10 WORKER)
        print("Is Yatirim'dan tum hisseler icin net borc cekiliyor (paralel)...")
        all_syms = list(self._all_data.keys())

        import requests
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import re as re_mod

        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        def isy_tek_hisse(kod):
            try:
                url = f'https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/sirket-karti.aspx?hisse={kod}'
                resp = session.get(url, timeout=15)
                html = resp.text
                net_borc = 0.0
                idx_nb = html.find('Net Bor')
                if idx_nb > 0:
                    chunk = html[idx_nb:idx_nb+200]
                    m = re_mod.search(r'(-?[\d\.]+,\d)\s*mnTL', chunk)
                    if m:
                        net_borc = float(m.group(1).replace('.', '').replace(',', '.')) * 1_000_000
                return kod, net_borc
            except Exception:
                return kod, 0.0

        nd_count = 0
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(isy_tek_hisse, kod): kod for kod in all_syms}
            done = 0
            for future in as_completed(futures):
                done += 1
                if done % 100 == 0:
                    print(f"  [{done}/{len(all_syms)}] Is Yatirim net borc...")
                kod, net_borc = future.result()
                if net_borc != 0 and kod in self._all_data:
                    self._all_data[kod]["net_debt_mn"] = net_borc / 1_000_000
                    self._all_data[kod]["net_debt"] = net_borc
                    nd_count += 1

        print(f"  Is Yatirim: {nd_count}/{len(all_syms)} hissede net borc bulundu")

        # Yahoo Finance - sadece F/K guncelleme (BIST 30)
        important = [
            "THYAO", "SISE", "ASELS", "BIMAS", "KCHOL", "EREGL", "SAHOL", "TCELL",
            "TOASO", "TUPRS", "FROTO", "TTKOM", "PGSUS", "KONYA", "PETKM",
            "ENKAI", "KOZAL", "KOZAA", "TAVHL", "DOHOL", "KONTR", "SASA", "ODAS", "A1CAP",
        ]
        print("Yahoo Finance ile BIST 30 guncelleniyor...")
        for i, code in enumerate(important):
            if progress_callback:
                progress_callback(i + 1, len(important), code)
            else:
                print(f"  [{i+1}/{len(important)}] {code}")
            try:
                company = self.yahoo.get_company_data(code)
                if company and code in self._all_data:
                    if not self._all_data[code].get("pe"):
                        self._all_data[code]["pe"] = company.get("pe")
                    if not self._all_data[code].get("pb"):
                        self._all_data[code]["pb"] = company.get("pb")
                time.sleep(0.3)
            except Exception as e:
                print(f"  {code} hatasi: {e}")

        # Deger analizi hesapla
        print("Deger analizleri hesaplaniyor...")
        BANKS = {"ISCTR", "GARAN", "AKBNK", "YKBNK", "HALKB", "VAKBN", "TSKB", "SEKFK"}
        for code in list(self._all_data.keys()):
            d = self._all_data[code]
            price = d.get("last_price", 0) or 0
            mcap = d.get("market_cap", 0) or 0
            ndebt = d.get("net_debt", 0) or 0
            frate = d.get("float_rate", 0) or 0
            fshares = d.get("floating_shares", 0) or 0

            if mcap > 0 and fshares > 0:
                # Bankalar icin net borc kullanma (is modeli geregi yuksek)
                if code in BANKS:
                    ev = mcap * (frate / 100)
                else:
                    ev = (mcap - ndebt) * (frate / 100)
                calc_val = ev / fshares if fshares > 0 else 0
                ratio = price / calc_val if calc_val > 0 else 0
                exp_ret = ((calc_val - price) / price * 100) if price > 0 else 0

                d["calculated_value"] = round(calc_val, 2)
                d["ratio"] = round(ratio, 2)
                d["expected_return"] = round(exp_ret, 1)

                # Sinyal
                if ratio > 3:
                    d["signal"] = "Hemen SAT"
                elif ratio > 1.5:
                    d["signal"] = "SAT"
                elif ratio > 0.99:
                    d["signal"] = "Kafana Gore"
                elif ratio > 0.7:
                    d["signal"] = "AL"
                elif ratio > 0.000001:
                    d["signal"] = "Evi Barki Sat"
                elif ratio < 0:
                    d["signal"] = "Borclu"
                else:
                    d["signal"] = "Deger Giriniz"
            else:
                d["calculated_value"] = 0
                d["ratio"] = 0
                d["expected_return"] = 0
                d["signal"] = "Veri Yetersiz"

        # Merkezi veritabanina hisse metadata yaz
        for code, item in self._all_data.items():
            company_name = str(item.get("company_name") or "").strip()
            sector = str(item.get("sector") or "").strip()
            self.db.upsert_stock(code, company_name=company_name, sector=sector)
            self.db.upsert_stock_market_data(
                code,
                source="Mynet fiyat | KAP fiili dolasim | IsYatirim/isyatirimhisse finansal",
                last_price=item.get("last_price"),
                change_pct=item.get("change_pct"),
                volume=item.get("volume"),
                market_cap=item.get("market_cap"),
                net_debt=item.get("net_debt"),
                total_shares=item.get("total_shares"),
                float_rate=item.get("float_rate"),
                floating_shares=item.get("floating_shares"),
                pe=item.get("pe"),
                pb=item.get("pb"),
                calculated_value=item.get("calculated_value"),
                ratio=item.get("ratio"),
                signal=item.get("signal"),
            )

        # Cache'le
        self.save_cache()
        return self._all_data

    def save_cache(self):
        """Verileri JSON dosyasina kaydeder."""
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._all_data, f, ensure_ascii=False, indent=2)
            with open(CACHE_TIME_FILE, "w") as f:
                f.write(datetime.now().isoformat())
        except Exception as e:
            print(f"Cache kayit hatasi: {e}")

    def backup_data(self):
        """Mevcut veriyi backup dosyasina kopyalar."""
        try:
            if CACHE_FILE.exists():
                import shutil
                shutil.copy2(CACHE_FILE, BACKUP_FILE)
                if CACHE_TIME_FILE.exists():
                    shutil.copy2(CACHE_TIME_FILE, BACKUP_TIME_FILE)
                self._log_price_update("Backup alindi")
                return True
        except Exception as e:
            self._log_price_update(f"Backup hatasi: {e}")
        return False

    def load_cache_with_backup(self) -> dict:
        """Cache'den yukler. Ana cache bozulursa backup'tan yukler."""
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    self._all_data = json.load(f)
                if self._all_data:
                    return self._all_data
        except (json.JSONDecodeError, Exception) as e:
            self._log_price_update(f"Ana cache bozuldu, backup'tan yukleniyor: {e}")

        # Ana cache bozuldu veya bos, backup'tan yukle
        try:
            if BACKUP_FILE.exists():
                with open(BACKUP_FILE, "r", encoding="utf-8") as f:
                    self._all_data = json.load(f)
                self._log_price_update(f"Backup'tan {len(self._all_data)} hisse yuklendi")
                # Backup'i ana cache'e yaz
                self.save_cache()
                return self._all_data
        except Exception as e:
            self._log_price_update(f"Backup okuma hatasi: {e}")

        return {}

    def update_prices_only(self) -> dict:
        """Sadece Mynet'ten fiyat cekip gunceller. Diger verileri degistirmez."""
        try:
            self._log_price_update("Fiyat guncellemesi basliyor...")

            # Once mevcut veriyi yukle (yoksa bos dict)
            if not self._all_data:
                self.load_cache_with_backup()

            # Mynet'ten taze fiyat cek
            mynet = MynetFetcher()
            stocks = mynet.fetch_all()

            if not stocks:
                self._log_price_update("Mynet'ten veri cekilemedi!")
                return self._all_data

            updated_count = 0
            for s in stocks:
                code = s["stock_code"]
                if code in self._all_data:
                    old_price = self._all_data[code].get("last_price", 0)
                    self._all_data[code]["last_price"] = s.get("last_price", 0)
                    self._all_data[code]["change_pct"] = s.get("change_pct", 0)
                    self._all_data[code]["change_direction"] = s.get("change_direction", "flat")
                    self._all_data[code]["volume"] = s.get("volume", 0)
                    if s.get("company_name"):
                        self._all_data[code]["company_name"] = s["company_name"]
                    if s.get("sector"):
                        self._all_data[code]["sector"] = s["sector"]
                    updated_count += 1

            # Deger analizini yeniden hesapla (fiyat degisti, ratio degisir)
            self._recalculate_signals()

            for code, item in self._all_data.items():
                if code in {s["stock_code"] for s in stocks}:
                    self.db.upsert_stock_market_data(
                        code,
                        source="Mynet fiyat | KAP fiili dolasim | IsYatirim/isyatirimhisse finansal",
                        last_price=item.get("last_price"),
                        change_pct=item.get("change_pct"),
                        volume=item.get("volume"),
                        market_cap=item.get("market_cap"),
                        net_debt=item.get("net_debt"),
                        total_shares=item.get("total_shares"),
                        float_rate=item.get("float_rate"),
                        floating_shares=item.get("floating_shares"),
                        pe=item.get("pe"),
                        pb=item.get("pb"),
                        calculated_value=item.get("calculated_value"),
                        ratio=item.get("ratio"),
                        signal=item.get("signal"),
                    )

            # Kaydet
            self.save_cache()
            msg = f"Fiyat guncellendi: {updated_count}/{len(stocks)} hisse"
            self._log_price_update(msg)
            print(f"[PriceUpdater] {msg}")

            return self._all_data

        except Exception as e:
            self._log_price_update(f"Fiyat guncelleme hatasi: {e}")
            print(f"[PriceUpdater] Hata: {e}")
            return self._all_data

    def update_single_price(self, symbol: str) -> dict:
        """Tek bir hissenin fiyatini cache ve merkezi veritabaninda yeniler."""
        code = str(symbol or "").strip().upper()
        if not code:
            return {}
        if not self._all_data:
            self.load_cache_with_backup()

        price_data = MynetFetcher().get_price(code)
        if not price_data or not price_data.get("last_price"):
            return {}

        item = self._all_data.setdefault(code, {"stock_code": code})
        item["last_price"] = price_data.get("last_price", 0)
        item["change_pct"] = price_data.get("change_pct", 0)
        item["change_direction"] = price_data.get("change_direction", "flat")
        item["volume"] = price_data.get("volume", 0)
        if price_data.get("company_name"):
            item["company_name"] = price_data["company_name"]
        if price_data.get("sector"):
            item["sector"] = price_data["sector"]

        self._recalculate_signals()
        self.db.upsert_stock(
            code,
            company_name=item.get("company_name", ""),
            sector=item.get("sector", ""),
        )
        self.db.upsert_stock_market_data(
            code,
            source="Mynet fiyat | KAP fiili dolasim | IsYatirim/isyatirimhisse finansal",
            last_price=item.get("last_price"),
            change_pct=item.get("change_pct"),
            volume=item.get("volume"),
            market_cap=item.get("market_cap"),
            net_debt=item.get("net_debt"),
            total_shares=item.get("total_shares"),
            float_rate=item.get("float_rate"),
            floating_shares=item.get("floating_shares"),
            pe=item.get("pe"),
            pb=item.get("pb"),
            calculated_value=item.get("calculated_value"),
            ratio=item.get("ratio"),
            signal=item.get("signal"),
        )
        self.save_cache()
        return item

    def _recalculate_signals(self):
        """Fiyat guncellemesinden sonra sinyalleri yeniden hesaplar."""
        BANKS = {"ISCTR", "GARAN", "AKBNK", "YKBNK", "HALKB", "VAKBN", "TSKB", "SEKFK"}
        for code in list(self._all_data.keys()):
            d = self._all_data[code]
            price = d.get("last_price", 0) or 0
            mcap = d.get("market_cap", 0) or 0
            ndebt = d.get("net_debt", 0) or 0
            frate = d.get("float_rate", 0) or 0
            fshares = d.get("floating_shares", 0) or 0

            if mcap > 0 and fshares > 0:
                if code in BANKS:
                    ev = mcap * (frate / 100)
                else:
                    ev = (mcap - ndebt) * (frate / 100)
                calc_val = ev / fshares if fshares > 0 else 0
                ratio = price / calc_val if calc_val > 0 else 0
                exp_ret = ((calc_val - price) / price * 100) if price > 0 else 0

                d["calculated_value"] = round(calc_val, 2)
                d["ratio"] = round(ratio, 2)
                d["expected_return"] = round(exp_ret, 1)

                if ratio > 3:
                    d["signal"] = "Hemen SAT"
                elif ratio > 1.5:
                    d["signal"] = "SAT"
                elif ratio > 0.99:
                    d["signal"] = "Kafana Gore"
                elif ratio > 0.7:
                    d["signal"] = "AL"
                elif ratio > 0.000001:
                    d["signal"] = "Evi Barki Sat"
                elif ratio < 0:
                    d["signal"] = "Borclu"
                else:
                    d["signal"] = "Deger Giriniz"

    def _log_price_update(self, message: str):
        """Fiyat guncelleme loglarini yazar."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(PRICE_UPDATE_LOG, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass

    def load_cache(self) -> dict:
        """Cache'den verileri yukler."""
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    self._all_data = json.load(f)
                return self._all_data
        except Exception as e:
            print(f"Cache okuma hatasi: {e}")
        return {}

    def get_cache_time(self) -> str:
        """Son guncelleme zamanini dondurur."""
        try:
            if CACHE_TIME_FILE.exists():
                with open(CACHE_TIME_FILE, "r") as f:
                    return f.read().strip()
        except Exception:
            pass
        return "Bilinmiyor"

    def is_cache_valid(self, max_age_seconds: int = 3600) -> bool:
        """Cache gecerli mi kontrol eder (1 saat varsayilan)."""
        try:
            if CACHE_TIME_FILE.exists():
                with open(CACHE_TIME_FILE, "r") as f:
                    last = datetime.fromisoformat(f.read().strip())
                    age = (datetime.now() - last).total_seconds()
                    return age < max_age_seconds
        except Exception:
            pass
        return False

    def get_all_data(self) -> dict:
        """Tum yuklenen verileri dondurur."""
        if not self._all_data:
            self.load_cache()
        return self._all_data

    def get_stock(self, symbol: str) -> dict:
        """Tekil hisse verisini dondurur."""
        if not self._all_data:
            self.load_cache()
        return self._all_data.get(symbol.upper(), {})

    def get_sorted_stocks(self, sort_by: str = "market_cap", ascending: bool = False) -> list:
        """Siralanmis hisse listesi dondurur."""
        data = list(self._all_data.values())
        return sorted(data, key=lambda x: x.get(sort_by, 0) or 0, reverse=not ascending)


if __name__ == "__main__":
    loader = DataPreloader()

    if loader.is_cache_valid(3600):
        print("Cache gecerli, yukleniyor...")
        loader.load_cache()
    else:
        print("Cache yok veya suresi dolmus, veriler cekiliyor...")
        loader.load_all()

    data = loader.get_all_data()
    print(f"\nToplam hisse: {len(data)}")

    # En buyuk 10 hisse
    print("\nEn Buyuk 10 Hisse (Piyasa Degeri):")
    sorted_stocks = loader.get_sorted_stocks("market_cap_mn")
    for s in sorted_stocks[:10]:
        print(f"  {s['stock_code']}: {s.get('market_cap_mn', 0):,.0f} mn TL | {s.get('last_price', 0):.2f} TL | {s.get('signal', 'N/A')}")
