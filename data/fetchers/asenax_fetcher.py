import json
import subprocess
from typing import Optional, Dict, List


class AsenaxFetcher:
    """api.asenax.com'dan toplu hisse verisi ceker (hizli ve guvenilir)."""

    LIST_URL = "https://api.asenax.com/bist/list"
    TEK_URL = "https://api.asenax.com/bist/get/{}"

    def __init__(self):
        self._cache = {}

    def _api_istek(self, url: str, timeout: int = 15) -> Optional[dict]:
        """Asenax API'sinden JSON veri ceker."""
        try:
            result = subprocess.run(
                ['curl', '-s', '--max-time', str(timeout),
                 '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                 '-H', 'Accept: application/json',
                 '-H', 'Referer: https://finans.mynet.com/',
                 url],
                capture_output=True, text=True, timeout=timeout + 5
            )
            if result.stdout:
                data = json.loads(result.stdout)
                if data.get('code') == '0' and data.get('data'):
                    return data['data']
        except Exception:
            pass
        return None

    def hisse_listesi(self) -> List[Dict]:
        """Tum BIST hisselerinin listesini ceker."""
        data = self._api_istek(self.LIST_URL)
        if not data:
            return []
        return [{'kod': h['kod'], 'ad': h.get('ad', '')} for h in data if h.get('tip') == 'Hisse']

    def tek_hisse_verisi(self, kod: str) -> Optional[Dict]:
        """Tek hisse icin detayli veri ceker."""
        if kod in self._cache:
            return self._cache[kod]

        data = self._api_istek(self.TEK_URL.format(kod))
        if not data:
            return None

        yz = data.get('hisseYuzeysel')
        if not yz:
            return None

        result = {
            'kod': kod,
            'kapanis': float(yz.get('kapanis') or 0),
            'dunku_kapanis': float(yz.get('dunkukapanis') or 0),
            'acilis': float(yz.get('acilis') or 0),
            'yuksek': float(yz.get('yuksek') or 0),
            'dusuk': float(yz.get('dusuk') or 0),
            'hacim_lot': float(yz.get('hacimlot') or 0),
            'hacim_tl': float(yz.get('hacimtl') or 0),
            'yuzde_degisim': float(yz.get('yuzdedegisim') or 0),
            'sermaye': float(yz.get('sermaye') or 0),
            'piyasa_degeri': float(yz.get('piydeg') or 0),
            'net_kar': float(yz.get('netkar') or 0),
            'beta': float(yz.get('beta') or 0),
            'fiyat_kazanc': float(yz.get('fiyatkaz') or 0),
            'oz_sermaye': float(yz.get('ozsermaye') or 0),
            'sektor_id': yz.get('sektorid'),
            'tarih': yz.get('tarih', ''),
        }

        self._cache[kod] = result
        return result

    def tumunu_cek(self, progress_callback=None) -> Dict[str, Dict]:
        """Tum BIST hisselerini ceker (tek tek API, ~15 istek/saniye)."""
        hisseler = self.hisse_listesi()
        if not hisseler:
            print("Asenax hisse listesi alinamadi.")
            return {}

        toplam = len(hisseler)
        print(f"Asenax'tan {toplam} hisse cekiliyor...")
        sonuc = {}

        for i, h in enumerate(hisseler):
            kod = h['kod']
            veri = self.tek_hisse_verisi(kod)
            if veri and veri['kapanis'] > 0:
                sonuc[kod] = veri

            if progress_callback:
                progress_callback(i + 1, toplam, kod)

            # Rate limit: saniyede ~15 istek
            if (i + 1) % 15 == 0:
                import time
                time.sleep(1)

        print(f"Asenax: {len(sonuc)}/{toplam} hisse verisi alindi")
        return sonuc
